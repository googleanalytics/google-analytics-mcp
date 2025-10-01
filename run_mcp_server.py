#!/usr/bin/env python3
"""Wrapper to run the MCP server with proper environment."""

import sys
import os

# Set up paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # Import and run the server
    from analytics_mcp.server import run_server
    
    # Config path is optional - if provided, must exist and be accessible
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        if not os.path.exists(config_path):
            print(f"Error: Config file not found: {config_path}", file=sys.stderr)
            print(f"Usage: {sys.argv[0]} [config_path]", file=sys.stderr)
            print(f"  config_path: Optional OAuth config file (uses ADC if not provided)", file=sys.stderr)
            sys.exit(1)

        # Test file accessibility early to provide helpful error messages
        try:
            with open(config_path, 'r') as f:
                f.read(1)  # Try to read at least 1 byte
        except PermissionError:
            print(f"\n❌ ERROR: Permission denied accessing config file: {config_path}", file=sys.stderr)
            print(f"❌ This usually happens when the config file is on Desktop/Documents and Terminal lacks folder access.", file=sys.stderr)
            print("", file=sys.stderr)
            print("🔧 SOLUTION 1 (Recommended): Move your config file to an accessible location:", file=sys.stderr)
            print(f"   cp '{config_path}' '{project_root}/'", file=sys.stderr)
            print("   Then run the MCP server with the new path:", file=sys.stderr)
            print(f"   python {sys.argv[0]} '{project_root}/{os.path.basename(config_path)}'", file=sys.stderr)
            print("", file=sys.stderr)
            print("🔧 SOLUTION 2: Grant Terminal app access to the folder containing your config:", file=sys.stderr)
            print("   System Settings → Privacy & Security → Files and Folders → Terminal → Enable folder access", file=sys.stderr)
            print("   (Note: You may need to restart Terminal after granting permissions)", file=sys.stderr)
            print("", file=sys.stderr)
            print("💡 TIP: For MCP servers, it's best practice to keep config files in the project directory.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            error_msg = str(e).lower()
            if "operation not permitted" in error_msg or "permission denied" in error_msg:
                print(f"\n❌ ERROR: Permission error accessing config file: {config_path}", file=sys.stderr)
                print(f"❌ Details: {e}", file=sys.stderr)
                print(f"❌ This usually happens when the config file is on Desktop/Documents and Terminal lacks folder access.", file=sys.stderr)
                print("", file=sys.stderr)
                print("🔧 SOLUTION 1 (Recommended): Move your config file to an accessible location:", file=sys.stderr)
                print(f"   cp '{config_path}' '{project_root}/'", file=sys.stderr)
                print("   Then run the MCP server with the new path:", file=sys.stderr)
                print(f"   python {sys.argv[0]} '{project_root}/{os.path.basename(config_path)}'", file=sys.stderr)
                print("", file=sys.stderr)
                print("🔧 SOLUTION 2: Grant Terminal app access to the folder containing your config:", file=sys.stderr)
                print("   System Settings → Privacy & Security → Files and Folders → Terminal → Enable folder access", file=sys.stderr)
                print("   (Note: You may need to restart Terminal after granting permissions)", file=sys.stderr)
                print("", file=sys.stderr)
                print("💡 TIP: For MCP servers, it's best practice to keep config files in the project directory.", file=sys.stderr)
                sys.exit(1)

        print(f"✅ Using OAuth config file: {config_path}", file=sys.stderr)
    else:
        print(f"✅ Starting MCP server with Application Default Credentials", file=sys.stderr)
    
    run_server(config_path)
    
except Exception as e:
    error_msg = str(e).lower()
    if "cannot access config file" in error_msg and ("permission" in error_msg or "operation not permitted" in error_msg):
        print(f"\n❌ Server failed to start: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("🔧 This is likely a file permission issue. Please try one of these solutions:", file=sys.stderr)
        print("   1. Move your config file to the project directory", file=sys.stderr)
        print("   2. Grant Terminal app access to the folder containing your config file", file=sys.stderr)
        print("   3. Run the server from the folder containing your config file", file=sys.stderr)
        print("", file=sys.stderr)
        print("💡 For detailed instructions, run the server again to see the specific error message.", file=sys.stderr)
    else:
        print(f"\n❌ Server crashed with error: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("🔍 Full error details:", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        print("", file=sys.stderr)
        print("💡 If this persists, check the server logs or file an issue on GitHub.", file=sys.stderr)
    sys.exit(1)