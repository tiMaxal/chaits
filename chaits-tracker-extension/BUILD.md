# Building Chaits Tracker Extension

## Prerequisites

- Node.js 20.x or later
- npm (comes with Node.js)
- VS Code 1.85.0 or later

## Build Steps

### 1. Install Dependencies

```bash
cd chaits-tracker-extension
npm install
```

This installs:
- TypeScript compiler
- VS Code extension types
- ESLint for code quality
- Testing framework

### 2. Compile TypeScript

```bash
npm run compile
```

This compiles all `.ts` files in `src/` to JavaScript in `out/`.

**Watch mode** (auto-recompile on changes):
```bash
npm run watch
```

### 3. Package Extension

```bash
npm install -g @vscode/vsce  # One-time install
npm run package
```

Creates: `chaits-tracker-0.1.0.vsix`

### 4. Install Locally

```bash
npm run install-local
# Or manually:
code --install-extension chaits-tracker-0.1.0.vsix
```

## Development Workflow

### Testing During Development

1. Open extension folder in VS Code:
   ```bash
   code chaits-tracker-extension
   ```

2. Press **F5** to launch Extension Development Host
   - New VS Code window opens with extension loaded
   - Make code changes in original window
   - Changes apply on reload (Ctrl+R in dev window)

3. View debug output:
   - In original window: `Debug Console` tab
   - In dev window: `Help → Toggle Developer Tools`

### Project Structure

```
chaits-tracker-extension/
├── src/
│   ├── extension.ts         # Entry point
│   ├── timestampTracker.ts  # Core tracking logic
│   ├── settingsProvider.ts  # Settings UI
│   ├── timelineProvider.ts  # Timeline view
│   └── exportManager.ts     # Export functionality
├── out/                     # Compiled JS (gitignored)
├── media/                   # Icons and assets
├── package.json             # Extension manifest
├── tsconfig.json            # TypeScript config
└── README.md
```

### Key Files

**package.json**: Extension manifest
- Defines commands, views, settings
- Activation events
- VS Code API version requirements

**src/extension.ts**: Entry point
- `activate()` - Called when extension loads
- `deactivate()` - Cleanup on unload
- Command registration

**src/timestampTracker.ts**: Core tracking
- Watches chat session files
- Logs interactions with timestamps
- Handles storage

## Testing

### Manual Testing Checklist

- [ ] Install extension in clean VS Code
- [ ] Verify welcome screen appears
- [ ] Have Copilot conversation
- [ ] Check status bar shows clock icon (minimal)
- [ ] Run "Show Tracking Status" command
- [ ] View timeline (should show recent chat)
- [ ] Export data (verify file created)
- [ ] Check globalStorage has data
- [ ] Restart VS Code (data persists?)
- [ ] Change settings (takes effect?)

### Automated Tests

```bash
npm run test
```

*Note: Test suite not fully implemented yet - this is a TODO*

## Common Build Issues

### "Cannot find module 'vscode'"

**Fix**: Run `npm install`

The `@types/vscode` package must be in devDependencies.

### "tsc: command not found"

**Fix**: TypeScript not installed globally

```bash
npm install -g typescript
# Or use local version:
npx tsc
```

### Package command fails

**Fix**: Install vsce tool

```bash
npm install -g @vscode/vsce
```

### Extension won't load in dev host

**Fix**: Check compile errors

```bash
npm run compile
# Look for red error messages
```

## Publishing (Future)

### To VS Code Marketplace

1. Get publisher account: https://marketplace.visualstudio.com/manage
2. Create Personal Access Token (Azure DevOps)
3. Login with vsce:
   ```bash
   vsce login your-publisher-name
   ```
4. Publish:
   ```bash
   vsce publish
   ```

### To GitHub Releases

1. Build .vsix file
2. Create GitHub release
3. Attach .vsix as asset
4. Users download and install manually

## Updating Version

Edit `package.json`:
```json
{
  "version": "0.2.0"  // Increment
}
```

Then rebuild and repackage.

### Version Numbering

- **0.x.x** - Pre-release/beta
- **1.0.0** - First stable release
- **1.1.0** - New features (minor)
- **1.0.1** - Bug fixes (patch)

## Scripts Reference

All available npm scripts:

```bash
npm run compile          # Compile TypeScript
npm run watch            # Auto-compile on changes
npm run lint             # Check code style
npm run test             # Run tests
npm run package          # Create .vsix
npm run install-local    # Install built extension
npm run vscode:prepublish # Pre-publish prep
```

## Debugging

### Console Logging

```typescript
console.log('Debug message');  // Shows in Debug Console
```

### Breakpoints

1. Set breakpoint in TypeScript file
2. Press F5 to start debugging
3. Trigger the code in Extension Dev Host
4. Debugger pauses at breakpoint

### Output Channel

Create output for users to see:

```typescript
const output = vscode.window.createOutputChannel('Chaits Tracker');
output.appendLine('Status message');
output.show();
```

## Best Practices

### Code Style

- Use TypeScript strict mode
- Follow existing patterns
- Add JSDoc comments for public methods
- Run `npm run lint` before commits

### Testing

- Test on Windows, Mac, Linux
- Test with/without Settings Sync
- Test with multiple workspaces open
- Test privacy mode (content exclusion)

### Performance

- Lazy-load heavy operations
- Use async/await for file I/O
- Batch multiple changes
- Don't block activation

## Need Help?

- **VS Code Extension API**: https://code.visualstudio.com/api
- **Extension Examples**: https://github.com/microsoft/vscode-extension-samples
- **Publishing Guide**: https://code.visualstudio.com/api/working-with-extensions/publishing-extension
