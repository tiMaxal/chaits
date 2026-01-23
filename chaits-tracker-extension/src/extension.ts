import * as vscode from 'vscode';
import { TimestampTracker } from './timestampTracker';
import { SettingsProvider } from './settingsProvider';
import { TimelineProvider } from './timelineProvider';
import { ExportManager } from './exportManager';

let tracker: TimestampTracker;

export function activate(context: vscode.ExtensionContext) {
    console.log('Chaits Tracker is now active');

    // Initialize core components
    tracker = new TimestampTracker(context);
    const settingsProvider = new SettingsProvider(context);
    const timelineProvider = new TimelineProvider(context, tracker);
    const exportManager = new ExportManager(context, tracker);

    // Register views
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('chaitsSettings', settingsProvider),
        vscode.window.registerTreeDataProvider('chaitsTimeline', timelineProvider)
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('chaits.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'chaits');
        }),
        
        vscode.commands.registerCommand('chaits.viewTimeline', async () => {
            const timeline = await tracker.getRecentInteractions(50);
            const panel = vscode.window.createWebviewPanel(
                'chaitsTimeline',
                'Chaits Chat Timeline',
                vscode.ViewColumn.One,
                { enableScripts: true }
            );
            panel.webview.html = getTimelineHtml(timeline);
        }),

        vscode.commands.registerCommand('chaits.exportData', async () => {
            await exportManager.exportToChait();
        }),

        vscode.commands.registerCommand('chaits.showStatus', async () => {
            const stats = await tracker.getStats();
            vscode.window.showInformationMessage(
                `Chaits Tracker: ${stats.totalInteractions} interactions tracked across ${stats.sessions} sessions`,
                'View Timeline', 'Export Data'
            ).then(selection => {
                if (selection === 'View Timeline') {
                    vscode.commands.executeCommand('chaits.viewTimeline');
                } else if (selection === 'Export Data') {
                    vscode.commands.executeCommand('chaits.exportData');
                }
            });
        }),

        vscode.commands.registerCommand('chaits.setupPreferences', async () => {
            await runSetupWizard(context);
        })
    );

    // Show welcome message and setup wizard on first run
    const setupCompleted = vscode.workspace.getConfiguration('chaits.setup').get('completed', false);
    const hasShownWelcome = context.globalState.get('chaits.hasShownWelcome', false);
    if (!hasShownWelcome) {
        showWelcomeMessage(context);
        context.globalState.update('chaits.hasShownWelcome', true);
        
        // Prompt for date/time preferences setup
        if (!setupCompleted) {
            const setupChoice = await vscode.window.showInformationMessage(
                'Would you like to configure date/time display preferences for Chaits Tracker?',
                'Configure Now', 'Use Defaults', 'Remind Later'
            );
            if (setupChoice === 'Configure Now') {
                await runSetupWizard(context);
            } else if (setupChoice === 'Use Defaults') {
                await vscode.workspace.getConfiguration('chaits.setup').update('completed', true, vscode.ConfigurationTarget.Global);
            }
        }
    }

    // Start tracking
    tracker.startTracking();

    // Status bar item (minimal by default)
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBar.tooltip = 'Chaits Tracker: Click for status';
    statusBar.command = 'chaits.showStatus';
    
    // Update status bar based on user preference
    const updateStatusBar = () => {
        const config = vscode.workspace.getConfiguration('chaits');
        const mode = config.get<string>('ui.statusBar', 'icon');
        
        if (mode === 'hidden') {
            statusBar.hide();
        } else if (mode === 'text') {
            statusBar.text = '$(history) Chaits';
            statusBar.show();
        } else { // 'icon' - minimal
            statusBar.text = '$(history)';
            statusBar.show();
        }
    };
    
    updateStatusBar();
    context.subscriptions.push(
        statusBar,
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('chaits.ui.statusBar')) {
                updateStatusBar();
            }
        })
    );
}

async function runSetupWizard(context: vscode.ExtensionContext) {
    // Step 1: Detect current locale
    const vscodeLocale = JSON.parse(process.env.VSCODE_NLS_CONFIG || '{}').locale || 'en';
    const suggestedLocale = vscodeLocale.startsWith('en-AU') ? 'en-AU' : 
                           vscodeLocale.startsWith('en-GB') ? 'en-GB' : 
                           vscodeLocale.startsWith('en-US') ? 'en-US' : 'en-AU';

    const locale = await vscode.window.showQuickPick([
        { label: '🇦🇺 Australia', value: 'en-AU', description: 'DD/MM/YYYY, 24-hour time', picked: suggestedLocale === 'en-AU' },
        { label: '🇺🇸 United States', value: 'en-US', description: 'MM/DD/YYYY, 12-hour AM/PM', picked: suggestedLocale === 'en-US' },
        { label: '🇬🇧 United Kingdom', value: 'en-GB', description: 'DD/MM/YYYY, 24-hour time', picked: suggestedLocale === 'en-GB' },
        { label: '🌐 Auto-detect', value: 'auto', description: 'Use VS Code locale settings' }
    ], {
        placeHolder: 'Select your region for date/time formatting',
        title: 'Chaits Setup (1/4): Region'
    });

    if (!locale) return; // User cancelled

    // Step 2: Date format
    const dateFormatOptions = [
        { label: 'YYYY-MM-DD', description: 'ISO 8601 (2026-01-23) - recommended for sorting', value: 'YYYY-MM-DD' },
        { label: 'DD/MM/YYYY', description: 'Australian/UK format (23/01/2026)', value: 'DD/MM/YYYY' },
        { label: 'MM/DD/YYYY', description: 'US format (01/23/2026)', value: 'MM/DD/YYYY' },
        { label: 'DD-MMM-YYYY', description: 'Human-readable (23-Jan-2026)', value: 'DD-MMM-YYYY' },
        { label: 'Use locale default', description: 'Automatic based on region', value: 'locale' }
    ];

    const dateFormat = await vscode.window.showQuickPick(dateFormatOptions, {
        placeHolder: 'Select date display format',
        title: 'Chaits Setup (2/4): Date Format'
    });

    if (!dateFormat) return;

    // Step 3: Time format
    const timeFormat = await vscode.window.showQuickPick([
        { label: '24-hour', description: '14:30:45', value: '24hr' },
        { label: '12-hour', description: '2:30:45 PM', value: '12hr' },
        { label: 'Use locale default', description: 'Automatic based on region', value: 'locale' }
    ], {
        placeHolder: 'Select time display format',
        title: 'Chaits Setup (3/4): Time Format'
    });

    if (!timeFormat) return;

    // Step 4: Timezone
    const timezoneChoice = await vscode.window.showQuickPick([
        { label: 'Local system timezone', description: 'Use computer\'s timezone', value: 'local' },
        { label: 'Australia/Sydney', description: 'AEDT (UTC+11) / AEST (UTC+10)', value: 'Australia/Sydney' },
        { label: 'Australia/Melbourne', description: 'AEDT (UTC+11) / AEST (UTC+10)', value: 'Australia/Melbourne' },
        { label: 'Australia/Brisbane', description: 'AEST (UTC+10) - no DST', value: 'Australia/Brisbane' },
        { label: 'Australia/Perth', description: 'AWST (UTC+8)', value: 'Australia/Perth' },
        { label: 'UTC', description: 'Coordinated Universal Time', value: 'UTC' },
        { label: 'Custom...', description: 'Enter IANA timezone', value: 'custom' }
    ], {
        placeHolder: 'Select timezone for timestamps',
        title: 'Chaits Setup (4/4): Timezone'
    });

    if (!timezoneChoice) return;

    let timezone = timezoneChoice.value;
    if (timezone === 'custom') {
        const customTz = await vscode.window.showInputBox({
            prompt: 'Enter IANA timezone (e.g., America/New_York, Europe/London)',
            placeHolder: 'America/New_York',
            validateInput: (value) => {
                try {
                    Intl.DateTimeFormat(undefined, { timeZone: value });
                    return null;
                } catch {
                    return 'Invalid timezone. See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones';
                }
            }
        });
        if (!customTz) return;
        timezone = customTz;
    }

    // Save all preferences
    const config = vscode.workspace.getConfiguration('chaits.format');
    await config.update('locale', locale.value, vscode.ConfigurationTarget.Global);
    await config.update('dateFormat', dateFormat.value, vscode.ConfigurationTarget.Global);
    await config.update('timeFormat', timeFormat.value, vscode.ConfigurationTarget.Global);
    await config.update('timezone', timezone, vscode.ConfigurationTarget.Global);
    await vscode.workspace.getConfiguration('chaits.setup').update('completed', true, vscode.ConfigurationTarget.Global);

    vscode.window.showInformationMessage(
        `✅ Date/time preferences saved: ${dateFormat.label} ${timeFormat.label}`,
        'View Settings'
    ).then(selection => {
        if (selection === 'View Settings') {
            vscode.commands.executeCommand('workbench.action.openSettings', 'chaits.format');
        }
    });
}

function showWelcomeMessage(context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        'chaitsWelcome',
        'Welcome to Chaits Tracker',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );

    panel.webview.html = getWelcomeHtml();

    // Handle messages from webview
    panel.webview.onDidReceiveMessage(
        message => {
            switch (message.command) {
                case 'configure':
                    vscode.commands.executeCommand('chaits.openSettings');
                    break;
                case 'close':
                    panel.dispose();
                    break;
            }
        },
        undefined,
        context.subscriptions
    );
}

function getWelcomeHtml(): string {
    return `<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Chaits Tracker</title>
        <style>
            body {
                font-family: var(--vscode-font-family);
                padding: 20px;
                line-height: 1.6;
                max-width: 700px;
                margin: 0 auto;
            }
            h1 {
                color: var(--vscode-foreground);
                border-bottom: 2px solid var(--vscode-panel-border);
                padding-bottom: 10px;
            }
            h2 {
                color: var(--vscode-foreground);
                margin-top: 30px;
            }
            .feature {
                background: var(--vscode-editor-background);
                border: 1px solid var(--vscode-panel-border);
                border-radius: 5px;
                padding: 15px;
                margin: 15px 0;
            }
            .feature-title {
                font-weight: bold;
                color: var(--vscode-textLink-foreground);
                margin-bottom: 8px;
            }
            button {
                background: var(--vscode-button-background);
                color: var(--vscode-button-foreground);
                border: none;
                padding: 10px 20px;
                margin: 10px 5px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 14px;
            }
            button:hover {
                background: var(--vscode-button-hoverBackground);
            }
            .button-container {
                margin-top: 30px;
                text-align: center;
            }
            .info-box {
                background: var(--vscode-inputValidation-infoBackground);
                border-left: 4px solid var(--vscode-inputValidation-infoBorder);
                padding: 15px;
                margin: 20px 0;
            }
            code {
                background: var(--vscode-textCodeBlock-background);
                padding: 2px 6px;
                border-radius: 3px;
                font-family: var(--vscode-editor-font-family);
            }
        </style>
    </head>
    <body>
        <h1>🎯 Welcome to Chaits Tracker</h1>
        
        <p>Thank you for installing <strong>Chaits Tracker</strong>! This extension solves a critical problem: tracking when you actually interact with Copilot across all your workspaces.</p>

        <h2>🚀 What This Extension Does</h2>
        
        <div class="feature">
            <div class="feature-title">📝 Per-Message Timestamps</div>
            Records the exact time of every Copilot chat interaction - not just when the conversation started.
        </div>

        <div class="feature">
            <div class="feature-title">🌐 Cross-Workspace & Cross-Chat Tracking</div>
            Tracks all chats across every workspace and correlates activity when you switch between different chat sessions within a project. Perfect for agentic workflows or multi-topic development sessions.
        </div>

        <div class="feature">
            <div class="feature-title">🔄 Automatic Sync</div>
            Uses VS Code Settings Sync to automatically deploy to all your machines - set it up once, works everywhere.
        </div>

        <div class="feature">
            <div class="feature-title">🗂️ Chaits Integration</div>
            Exports data in chaits-compatible format for advanced timeline analysis and project progression tracking.
        </div>

        <div class="feature">
            <div class="feature-title">🔗 Git Correlation</div>
            Links chat interactions with Git commits to reconstruct your complete development timeline.
        </div>

        <h2>✅ You're Ready!</h2>
        
        <div class="info-box">
            <strong>Tracking is already enabled!</strong><br>
            The extension is now recording timestamps for all your Copilot chats. Data is stored in:
            <br><br>
            <code>%APPDATA%/Code/User/globalStorage/chaits-tracker/</code>
        </div>

        <h2>🎛️ Optional Configuration</h2>
        
        <p>The default settings work great, but you can customize:</p>
        <ul>
            <li><strong>Privacy</strong>: Disable content storage (timestamps only)</li>
            <li><strong>Export path</strong>: Set custom location for chaits exports</li>
            <li><strong>Auto-export</strong>: Enable daily automatic exports</li>
            <li><strong>Exclude workspaces</strong>: Skip tracking for specific projects</li>
        </ul>

        <div class="button-container">
            <button onclick="configure()">⚙️ Configure Settings</button>
            <button onclick="close()">✨ Start Using</button>
        </div>

        <script>
            const vscode = acquireVsCodeApi();
            
            function configure() {
                vscode.postMessage({ command: 'configure' });
            }
            
            function close() {
                vscode.postMessage({ command: 'close' });
            }
        </script>
    </body>
    </html>`;
}

function getTimelineHtml(timeline: any[]): string {
    const rows = timeline.map(item => {
        const date = new Date(item.timestamp);
        const role = item.role === 'user' ? '👤 You' : '🤖 Copilot';
        const preview = item.content.substring(0, 100) + (item.content.length > 100 ? '...' : '');
        return `
            <tr>
                <td>${date.toLocaleString()}</td>
                <td>${role}</td>
                <td>${item.workspace || 'Unknown'}</td>
                <td>${preview}</td>
            </tr>
        `;
    }).join('');

    return `<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chaits Timeline</title>
        <style>
            body {
                font-family: var(--vscode-font-family);
                padding: 20px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                text-align: left;
                padding: 8px;
                border-bottom: 1px solid var(--vscode-panel-border);
            }
            th {
                background: var(--vscode-editor-background);
                font-weight: bold;
            }
            tr:hover {
                background: var(--vscode-list-hoverBackground);
            }
        </style>
    </head>
    <body>
        <h1>Recent Chat Timeline</h1>
        <table>
            <tr>
                <th>Time</th>
                <th>Who</th>
                <th>Workspace</th>
                <th>Message Preview</th>
            </tr>
            ${rows}
        </table>
    </body>
    </html>`;
}

export function deactivate() {
    if (tracker) {
        tracker.stopTracking();
    }
}
