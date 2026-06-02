import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { TimestampTracker } from './timestampTracker';

interface LoggedInteraction {
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
    workspaceHash?: string;
    workspaceName?: string;
}

interface ExportMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
}

interface ExportConversation {
    conversation_id: string;
    conversation_title: string;
    create_time: number;
    workspace: string;
    messages: ExportMessage[];
}

export class ExportManager {
    constructor(
        private context: vscode.ExtensionContext,
        private tracker: TimestampTracker
    ) {
        // Setup auto-export if enabled
        const config = vscode.workspace.getConfiguration('chaits.export');
        if (config.get('autoExport', false)) {
            this.scheduleAutoExport();
        }
    }

    private scheduleAutoExport() {
        // Export daily at midnight
        const now = new Date();
        const tomorrow = new Date(now);
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        
        const timeUntilMidnight = tomorrow.getTime() - now.getTime();
        
        setTimeout(() => {
            this.exportToChait();
            // Reschedule for next day
            setInterval(() => this.exportToChait(), 24 * 60 * 60 * 1000);
        }, timeUntilMidnight);
    }

    public async exportToChait(): Promise<void> {
        try {
            const config = vscode.workspace.getConfiguration('chaits.export');
            let exportPath = config.get('path', '') as string;

            // Default to chaits directory structure
            if (!exportPath) {
                const workspaceFolders = vscode.workspace.workspaceFolders;
                if (workspaceFolders && workspaceFolders.length > 0) {
                    const workspaceRoot = workspaceFolders[0].uri.fsPath;
                    exportPath = path.join(workspaceRoot, '.aiccounts', 'accounts_copilot', 'exports');
                } else {
                    // Fallback to user's home directory
                    const home = process.env.USERPROFILE || process.env.HOME || '';
                    exportPath = path.join(home, '.aiccounts', 'accounts_copilot', 'exports');
                }
            }

            // Ensure export directory exists
            if (!fs.existsSync(exportPath)) {
                fs.mkdirSync(exportPath, { recursive: true });
            }

            // Read all interaction logs
            const storageDir = this.tracker.getStorageDir();
            const trackedConversations = await this.buildConversations(storageDir);
            const workspaceConversations = await this.buildConversationsFromWorkspaceSessions();
            const conversations = this.mergeConversations(trackedConversations, workspaceConversations);

            // Export in chaits-compatible format
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
            const outputFile = path.join(exportPath, `vscode_copilot_tracked_${timestamp}.json`);

            const exportData = {
                export_source: 'chaits-tracker-extension',
                export_timestamp: Date.now(),
                version: '1.0',
                conversations
            };

            fs.writeFileSync(outputFile, JSON.stringify(exportData, null, 2));

            vscode.window.showInformationMessage(
                `✅ Exported ${conversations.length} conversations to ${path.basename(outputFile)}`,
                'Open Folder', 'Open in Chaits'
            ).then(selection => {
                if (selection === 'Open Folder') {
                    vscode.env.openExternal(vscode.Uri.file(exportPath));
                } else if (selection === 'Open in Chaits') {
                    // Future: launch chaits with this export
                }
            });

        } catch (err: any) {
            vscode.window.showErrorMessage(`Export failed: ${err.message}`);
        }
    }

    private async buildConversations(storageDir: string): Promise<ExportConversation[]> {
        const sessionFiles = fs.readdirSync(storageDir)
            .filter(f => f.startsWith('session-') && f.endsWith('.jsonl'));

        const currentWorkspaceHash = this.tracker.getCurrentWorkspaceHash();
        const currentWorkspaceName = this.tracker.getCurrentWorkspaceName();

        const conversations: ExportConversation[] = [];

        for (const sessionFile of sessionFiles) {
            const sessionId = sessionFile.replace('session-', '').replace('.jsonl', '');
            const filePath = path.join(storageDir, sessionFile);
            const lines = fs.readFileSync(filePath, 'utf-8').split('\n').filter(l => l.trim());

            if (lines.length === 0) continue;

            const messages = [];
            let title = 'Untitled Chat';
            let createTime = 0;
            let workspace = '';

            for (const line of lines) {
                try {
                    const interaction = JSON.parse(line) as LoggedInteraction;
                    if (!this.isCurrentWorkspaceInteraction(interaction, currentWorkspaceHash, currentWorkspaceName)) {
                        continue;
                    }
                    
                    // Use first message timestamp as conversation create time
                    if (createTime === 0) {
                        createTime = interaction.timestamp;
                    }
                    
                    workspace = interaction.workspaceName || workspace;

                    messages.push({
                        role: interaction.role,
                        content: interaction.content,
                        timestamp: interaction.timestamp
                    });

                    // Try to extract title from first user message
                    if (interaction.role === 'user' && title === 'Untitled Chat') {
                        title = interaction.content.substring(0, 50).trim();
                        if (title.length < interaction.content.length) {
                            title += '...';
                        }
                    }
                } catch (err) {
                    // Skip malformed lines
                }
            }

            if (messages.length > 0) {
                conversations.push({
                    conversation_id: sessionId,
                    conversation_title: title,
                    create_time: Math.floor(createTime / 1000), // Convert to seconds
                    workspace,
                    messages
                });
            }
        }

        return conversations;
    }

    private async buildConversationsFromWorkspaceSessions(): Promise<ExportConversation[]> {
        const currentWorkspaceHash = this.tracker.getCurrentWorkspaceHash();
        const currentWorkspaceName = this.tracker.getCurrentWorkspaceName() || '';

        if (!currentWorkspaceHash) {
            return [];
        }

        const chatSessionsDir = path.join(
            this.tracker.getWorkspaceStoragePath(),
            currentWorkspaceHash,
            'chatSessions'
        );

        if (!fs.existsSync(chatSessionsDir)) {
            return [];
        }

        const sessionFiles = fs.readdirSync(chatSessionsDir)
            .filter((f: string) => f.endsWith('.json'));

        const conversations: ExportConversation[] = [];

        for (const sessionFile of sessionFiles) {
            const sessionPath = path.join(chatSessionsDir, sessionFile);

            try {
                const session = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
                const sessionId = session.sessionId || path.basename(sessionFile, '.json');
                const requests = Array.isArray(session.requests) ? session.requests : [];

                if (requests.length === 0) {
                    continue;
                }

                const messages: ExportMessage[] = [];
                let title = typeof session.customTitle === 'string' && session.customTitle.trim()
                    ? session.customTitle.trim()
                    : 'Untitled Chat';
                let createTimeMs = this.toTimestampMs(session.creationDate);

                for (const req of requests) {
                    const reqTimestamp = this.toTimestampMs(req?.timestamp);
                    if (createTimeMs === 0 && reqTimestamp > 0) {
                        createTimeMs = reqTimestamp;
                    }

                    if (req?.message?.text) {
                        const text = String(req.message.text);
                        messages.push({
                            role: 'user',
                            content: text,
                            timestamp: reqTimestamp || createTimeMs || Date.now()
                        });

                        if (title === 'Untitled Chat') {
                            title = text.substring(0, 50).trim();
                            if (title.length < text.length) {
                                title += '...';
                            }
                        }
                    }

                    const responseContent = this.extractResponseContent(req?.response?.value);
                    if (responseContent) {
                        messages.push({
                            role: 'assistant',
                            content: responseContent,
                            timestamp: reqTimestamp || createTimeMs || Date.now()
                        });
                    }
                }

                if (messages.length === 0) {
                    continue;
                }

                if (createTimeMs === 0) {
                    createTimeMs = messages[0].timestamp;
                }

                conversations.push({
                    conversation_id: String(sessionId),
                    conversation_title: title,
                    create_time: Math.floor(createTimeMs / 1000),
                    workspace: currentWorkspaceName,
                    messages
                });
            } catch {
                // Skip malformed session files.
            }
        }

        return conversations;
    }

    private mergeConversations(
        trackedConversations: ExportConversation[],
        workspaceConversations: ExportConversation[]
    ): ExportConversation[] {
        const merged = new Map<string, ExportConversation>();

        for (const conversation of trackedConversations) {
            merged.set(conversation.conversation_id, conversation);
        }

        for (const conversation of workspaceConversations) {
            const existing = merged.get(conversation.conversation_id);
            if (!existing) {
                merged.set(conversation.conversation_id, conversation);
                continue;
            }

            const existingNewest = this.getNewestTimestamp(existing.messages);
            const candidateNewest = this.getNewestTimestamp(conversation.messages);

            if (
                conversation.messages.length > existing.messages.length ||
                candidateNewest > existingNewest
            ) {
                merged.set(conversation.conversation_id, conversation);
            }
        }

        return Array.from(merged.values());
    }

    private getNewestTimestamp(messages: ExportMessage[]): number {
        let newest = 0;
        for (const message of messages) {
            if (message.timestamp > newest) {
                newest = message.timestamp;
            }
        }
        return newest;
    }

    private toTimestampMs(value: unknown): number {
        if (typeof value === 'number' && Number.isFinite(value)) {
            return value < 1e12 ? Math.floor(value * 1000) : Math.floor(value);
        }

        if (typeof value === 'string' && value.trim()) {
            const parsedAsNumber = Number(value);
            if (Number.isFinite(parsedAsNumber)) {
                return parsedAsNumber < 1e12 ? Math.floor(parsedAsNumber * 1000) : Math.floor(parsedAsNumber);
            }

            const parsedDate = Date.parse(value);
            if (!Number.isNaN(parsedDate)) {
                return parsedDate;
            }
        }

        return 0;
    }

    private extractResponseContent(value: unknown): string {
        if (Array.isArray(value)) {
            const parts: string[] = [];
            for (const item of value) {
                if (typeof item === 'string') {
                    parts.push(item);
                    continue;
                }

                if (item && typeof item === 'object' && 'value' in item) {
                    const outerValue = (item as { value?: unknown }).value;
                    if (typeof outerValue === 'string') {
                        parts.push(outerValue);
                        continue;
                    }

                    if (outerValue && typeof outerValue === 'object' && 'value' in outerValue) {
                        const nestedValue = (outerValue as { value?: unknown }).value;
                        if (typeof nestedValue === 'string') {
                            parts.push(nestedValue);
                        }
                    }
                }
            }
            return parts.join('\n').trim();
        }

        if (typeof value === 'string') {
            return value.trim();
        }

        return '';
    }

    private isCurrentWorkspaceInteraction(
        interaction: LoggedInteraction,
        currentWorkspaceHash: string | null,
        currentWorkspaceName: string | null
    ): boolean {
        if (currentWorkspaceHash) {
            if (interaction.workspaceHash) {
                return interaction.workspaceHash === currentWorkspaceHash;
            }
            if (currentWorkspaceName && interaction.workspaceName) {
                return interaction.workspaceName === currentWorkspaceName;
            }
            return false;
        }

        if (!currentWorkspaceName) {
            return true;
        }

        return interaction.workspaceName === currentWorkspaceName;
    }
}
