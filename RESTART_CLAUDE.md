# How to Restart Claude Desktop to Pick Up MCP Server Changes

## The Issue
Claude Desktop caches the MCP server schema when it first connects. After making code changes to your MCP server, you need to restart Claude Desktop to pick up the new schema.

## Steps to Restart

### Windows:
1. **Completely quit Claude Desktop**
   - Right-click the Claude icon in the system tray (bottom-right corner)
   - Click "Quit" or "Exit"
   - OR: Press `Alt+F4` while Claude Desktop is focused

2. **Verify it's closed**
   - Open Task Manager (`Ctrl+Shift+Esc`)
   - Look for "Claude" in the Processes tab
   - If it's still running, right-click and select "End Task"

3. **Restart Claude Desktop**
   - Launch Claude Desktop from the Start menu or desktop shortcut

4. **Verify the MCP server reconnected**
   - Look for the MCP icon (🔌 or hammer) in Claude Desktop
   - It should show "hcdp" as connected

## What Changed
The latest fix allows `lat` and `lng` to accept both strings and floats:
- Before: `lat: float | None` (rejected strings like "-155.0833")
- After: `lat: float | str | None` (accepts both, converts strings to floats)

## Test Query
After restarting, try:
> "Get rainfall timeseries data for Hilo (19.7167, -155.0833) for 2024 with production level 'new' and period 'month'"
