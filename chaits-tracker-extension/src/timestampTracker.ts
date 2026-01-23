import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

interface ChatInteraction {
    timestamp: number;
    sessionId: string;
    role: 'user' | 'assistant';
    content: string;
    workspaceHash: string;
    workspaceName: string;
    fileContext?: string[];
    gitCommit?: string;
}

interface TrackerStats {
    totalInteractions: number;
    sessions: number;
    oldestTimestamp: number;
    newestTimestamp: number;
}

export class TimestampTracker {
    private context: vscode.ExtensionContext;
    private storageDir: string;
    private currentSessionId: string | null = null;
    private watcher: vscode.FileSystemWatcher | null = null;
    private gitWatcher: vscode.Disposable | null = null;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        
        // Use global storage for cross-workspace tracking
        this.storageDir = path.join(
            context.globalStorageUri.fsPath,
            'interaction-logs'
        );
        
        // Ensure storage directory exists
        if (!fs.existsSync(this.storageDir)) {
            fs.mkdirSync(this.storageDir, { recursive: true });
        }
    }

    public startTracking() {
        const config = vscode.workspace.getConfiguration('chaits.tracking');
        if (!config.get('enabled', true)) {
            console.log('Chaits tracking is disabled');
            return;
        }

        // Monitor workspace storage for chat sessions
        this.watchChatSessions();

        // Monitor Git activity if enabled
        if (vscode.workspace.getConfiguration('chaits.correlate').get('gitCommits', true)) {
            this.watchGitActivity();
        }

        // Monitor file edits if enabled
        if (vscode.workspace.getConfiguration('chaits.correlate').get('fileEdits', true)) {
            this.watchFileEdits();
        }

        console.log('Chaits tracking started');
    }

    public stopTracking() {
        if (this.watcher) {
            this.watcher.dispose();
        }
        if (this.gitWatcher) {
            this.gitWatcher.dispose();
        }
    }

    private watchChatSessions() {
        // Watch VS Code's workspace storage for chat session changes
        const appData = process.env.APPDATA || process.env.HOME + '/.config';
        const workspaceStoragePath = path.join(appData, 'Code', 'User', 'workspaceStorage');

        // Create file system watcher for chat sessions
        const pattern = new vscode.RelativePattern(workspaceStoragePath, '**/chatSessions/*.json');
        this.watcher = vscode.workspace.createFileSystemWatcher(pattern);

        this.watcher.onDidChange(uri => this.handleChatSessionChange(uri));
        this.watcher.onDidCreate(uri => this.handleChatSessionChange(uri));

        // Initial scan of existing sessions
        this.scanExistingSessions();
    }

    private async scanExistingSessions() {
        const appData = process.env.APPDATA || process.env.HOME + '/.config';
        const workspaceStoragePath = path.join(appData, 'Code', 'User', 'workspaceStorage');

        try {
            const workspaceDirs = fs.readdirSync(workspaceStoragePath);
            
            for (const workspaceDir of workspaceDirs) {
                const chatSessionsPath = path.join(workspaceStoragePath, workspaceDir, 'chatSessions');
                
                if (fs.existsSync(chatSessionsPath)) {
                    const sessionFiles = fs.readdirSync(chatSessionsPath).filter(f => f.endsWith('.json'));
                    
                    for (const sessionFile of sessionFiles) {
                        const sessionPath = path.join(chatSessionsPath, sessionFile);
                        await this.processChatSession(sessionPath, workspaceDir);
                    }
                }
            }
        } catch (err) {
            console.error('Error scanning existing sessions:', err);
        }
    }

    private async handleChatSessionChange(uri: vscode.Uri) {
        const workspaceHash = this.extractWorkspaceHash(uri.fsPath);
        await this.processChatSession(uri.fsPath, workspaceHash);
    }

    private async processChatSession(sessionPath: string, workspaceHash: string) {
        try {
            const content = fs.readFileSync(sessionPath, 'utf-8');
            const session = JSON.parse(content);

            const sessionId = session.sessionId || path.basename(sessionPath, '.json');
            const workspaceName = this.getWorkspaceName(workspaceHash);

            // Check if we've already processed this session version
            const sessionLogPath = path.join(this.storageDir, `${sessionId}.json`);
            let processedCount = 0;
            
            if (fs.existsSync(sessionLogPath)) {
                const log = JSON.parse(fs.readFileSync(sessionLogPath, 'utf-8'));
                processedCount = log.processedMessages || 0;
            }

            const requests = session.requests || [];
            
            // Process only new messages
            if (requests.length > processedCount) {
                const newRequests = requests.slice(processedCount);
                
                for (const req of newRequests) {
                    // User message
                    if (req.message && req.message.text) {
                        await this.logInteraction({
                            timestamp: Date.now(),
                            sessionId,
                            role: 'user',
                            content: req.message.text,
                            workspaceHash,
                            workspaceName,
                            fileContext: this.getOpenFiles()
                        });
                    }

                    // Assistant response
                    if (req.response && req.response.value) {
                        const responseContent = this.extractResponseContent(req.response.value);
                        if (responseContent) {
                            await this.logInteraction({
                                timestamp: Date.now(),
                                sessionId,
                                role: 'assistant',
                                content: responseContent,
                                workspaceHash,
                                workspaceName
                            });
                        }
                    }
                }

                // Update processed count
                this.updateSessionLog(sessionLogPath, {
                    sessionId,
                    processedMessages: requests.length,
                    lastUpdate: Date.now()
                });
            }
        } catch (err) {
            console.error('Error processing chat session:', err);
        }
    }

    private extractResponseContent(value: any): string {
        if (Array.isArray(value)) {
            const parts: string[] = [];
            for (const item of value) {
                if (typeof item === 'string') {
                    parts.push(item);
                } else if (item.value) {
                    if (typeof item.value === 'string') {
                        parts.push(item.value);
                    } else if (item.value.value) {
                        parts.push(String(item.value.value));
                    }
                }
            }
            return parts.join('\n');
        }
        return String(value);
    }

    private async logInteraction(interaction: ChatInteraction) {
        const config = vscode.workspace.getConfiguration('chaits.tracking');
        
        // Check if we should include content
        if (!config.get('includeContent', true)) {
            interaction.content = '[Content hidden - privacy mode enabled]';
        }

        // Check if workspace is excluded
        const excludedWorkspaces = config.get('privacy.excludeWorkspaces', []) as string[];
        if (excludedWorkspaces.includes(interaction.workspaceName)) {
            return;
        }

        // Append to daily log file
        const dateStr = new Date(interaction.timestamp).toISOString().split('T')[0];
        const logFile = path.join(this.storageDir, `interactions-${dateStr}.jsonl`);

        const logEntry = JSON.stringify(interaction) + '\n';
        fs.appendFileSync(logFile, logEntry);

        // Also maintain session-specific log
        const sessionLogFile = path.join(this.storageDir, `session-${interaction.sessionId}.jsonl`);
        fs.appendFileSync(sessionLogFile, logEntry);
    }

    private updateSessionLog(logPath: string, data: any) {
        fs.writeFileSync(logPath, JSON.stringify(data, null, 2));
    }

    private extractWorkspaceHash(sessionPath: string): string {
        const match = sessionPath.match(/workspaceStorage[\/\\]([^\/\\]+)/);
        return match ? match[1] : 'unknown';
    }

    private getWorkspaceName(hash: string): string {
        // Try to resolve workspace name from workspace.json
        const appData = process.env.APPDATA || process.env.HOME + '/.config';
        const workspacePath = path.join(appData, 'Code', 'User', 'workspaceStorage', hash, 'workspace.json');
        
        try {
            if (fs.existsSync(workspacePath)) {
                const workspace = JSON.parse(fs.readFileSync(workspacePath, 'utf-8'));
                if (workspace.folder) {
                    return path.basename(workspace.folder);
                }
            }
        } catch (err) {
            // Ignore
        }

        // Fallback to current workspace
        if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
            return path.basename(vscode.workspace.workspaceFolders[0].uri.fsPath);
        }

        return hash.substring(0, 8);
    }

    private getOpenFiles(): string[] {
        return vscode.window.visibleTextEditors
            .map(editor => editor.document.fileName)
            .filter(name => !name.startsWith('extension-output-'));
    }

    private watchGitActivity() {
        // Monitor Git extension for commit events
        const gitExtension = vscode.extensions.getExtension('vscode.git');
        if (gitExtension) {
            gitExtension.activate().then(git => {
                // Future: hook into Git commit events
                console.log('Git correlation enabled');
            });
        }
    }

    private watchFileEdits() {
        // Track file saves for correlation
        this.context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(doc => {
                // Log file edit timestamp
                const editLog = path.join(this.storageDir, 'file-edits.jsonl');
                const entry = JSON.stringify({
                    timestamp: Date.now(),
                    file: doc.fileName,
                    workspace: this.getWorkspaceName('')
                }) + '\n';
                fs.appendFileSync(editLog, entry);
            })
        );
    }

    public async getRecentInteractions(limit: number = 50): Promise<ChatInteraction[]> {
        const interactions: ChatInteraction[] = [];
        const files = fs.readdirSync(this.storageDir)
            .filter(f => f.startsWith('interactions-') && f.endsWith('.jsonl'))
            .sort()
            .reverse();

        for (const file of files) {
            const filePath = path.join(this.storageDir, file);
            const lines = fs.readFileSync(filePath, 'utf-8').split('\n').filter(l => l.trim());
            
            for (const line of lines.reverse()) {
                if (interactions.length >= limit) {
                    return interactions;
                }
                try {
                    interactions.push(JSON.parse(line));
                } catch (err) {
                    // Skip malformed lines
                }
            }
        }

        return interactions;
    }

    public async getStats(): Promise<TrackerStats> {
        let totalInteractions = 0;
        const sessions = new Set<string>();
        let oldestTimestamp = Infinity;
        let newestTimestamp = 0;

        const files = fs.readdirSync(this.storageDir)
            .filter(f => f.startsWith('interactions-') && f.endsWith('.jsonl'));

        for (const file of files) {
            const filePath = path.join(this.storageDir, file);
            const lines = fs.readFileSync(filePath, 'utf-8').split('\n').filter(l => l.trim());
            
            for (const line of lines) {
                try {
                    const interaction = JSON.parse(line);
                    totalInteractions++;
                    sessions.add(interaction.sessionId);
                    oldestTimestamp = Math.min(oldestTimestamp, interaction.timestamp);
                    newestTimestamp = Math.max(newestTimestamp, interaction.timestamp);
                } catch (err) {
                    // Skip
                }
            }
        }

        return {
            totalInteractions,
            sessions: sessions.size,
            oldestTimestamp: oldestTimestamp === Infinity ? 0 : oldestTimestamp,
            newestTimestamp
        };
    }

    public getStorageDir(): string {
        return this.storageDir;
    }
}
