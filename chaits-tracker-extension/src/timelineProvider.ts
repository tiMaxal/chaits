import * as vscode from 'vscode';
import { TimestampTracker } from './timestampTracker';

export class TimelineProvider implements vscode.TreeDataProvider<TimelineItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<TimelineItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    constructor(
        private context: vscode.ExtensionContext,
        private tracker: TimestampTracker
    ) {
        // Refresh periodically
        setInterval(() => this.refresh(), 30000); // Every 30 seconds
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: TimelineItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: TimelineItem): Promise<TimelineItem[]> {
        if (!element) {
            // Root level - show recent interactions grouped by session
            const interactions = await this.tracker.getRecentInteractions(20);
            const sessionMap = new Map<string, any[]>();

            for (const interaction of interactions) {
                if (!sessionMap.has(interaction.sessionId)) {
                    sessionMap.set(interaction.sessionId, []);
                }
                sessionMap.get(interaction.sessionId)!.push(interaction);
            }

            const items: TimelineItem[] = [];
            for (const [sessionId, messages] of sessionMap) {
                const firstMsg = messages[messages.length - 1];
                const time = new Date(firstMsg.timestamp);
                items.push(
                    new TimelineItem(
                        `${firstMsg.workspaceName || 'Unknown'}`,
                        `${time.toLocaleString()} • ${messages.length} messages`,
                        'session',
                        sessionId
                    )
                );
            }

            return items;
        }

        return [];
    }
}

class TimelineItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly description: string,
        public readonly type: 'session' | 'message',
        public readonly id: string
    ) {
        super(label, vscode.TreeItemCollapsibleState.None);
        this.tooltip = description;
        this.description = description;
        this.iconPath = type === 'session' 
            ? new vscode.ThemeIcon('comment-discussion')
            : new vscode.ThemeIcon('comment');
    }
}
