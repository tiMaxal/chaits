import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { TimestampTracker } from './timestampTracker';

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
            const conversations = await this.buildConversations(storageDir);

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

    private async buildConversations(storageDir: string): Promise<any[]> {
        const sessionFiles = fs.readdirSync(storageDir)
            .filter(f => f.startsWith('session-') && f.endsWith('.jsonl'));

        const conversations = [];

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
                    const interaction = JSON.parse(line);
                    
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
}
