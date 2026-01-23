import * as vscode from 'vscode';

export class SettingsProvider implements vscode.TreeDataProvider<SettingItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<SettingItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    constructor(private context: vscode.ExtensionContext) {
        // Watch for configuration changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('chaits')) {
                this.refresh();
            }
        });
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: SettingItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: SettingItem): Thenable<SettingItem[]> {
        if (!element) {
            return Promise.resolve(this.getRootSettings());
        }
        return Promise.resolve([]);
    }

    private getRootSettings(): SettingItem[] {
        const config = vscode.workspace.getConfiguration('chaits');
        
        return [
            new SettingItem(
                'Tracking Status',
                config.get('tracking.enabled') ? '✅ Enabled' : '❌ Disabled',
                'tracking.enabled',
                config.get('tracking.enabled')
            ),
            new SettingItem(
                'Storage Location',
                config.get('tracking.storage') === 'global' ? '🌐 Global (Synced)' : '📁 Workspace Only',
                'tracking.storage',
                config.get('tracking.storage')
            ),
            new SettingItem(
                'Content Tracking',
                config.get('tracking.includeContent') ? '📝 Full Content' : '🔒 Timestamps Only',
                'tracking.includeContent',
                config.get('tracking.includeContent')
            ),
            new SettingItem(
                'Git Correlation',
                config.get('correlate.gitCommits') ? '✅ Enabled' : '❌ Disabled',
                'correlate.gitCommits',
                config.get('correlate.gitCommits')
            ),
            new SettingItem(
                'Auto Export',
                config.get('export.autoExport') ? '✅ Enabled' : '❌ Disabled',
                'export.autoExport',
                config.get('export.autoExport')
            )
        ];
    }
}

class SettingItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly description: string,
        public readonly configKey: string,
        public readonly value: any
    ) {
        super(label, vscode.TreeItemCollapsibleState.None);
        this.tooltip = `${label}: ${description}\n\nClick to change`;
        this.description = description;
        this.command = {
            command: 'chaits.openSettings',
            title: 'Open Settings'
        };
    }
}
