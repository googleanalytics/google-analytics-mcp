#!/usr/bin/env python3
"""Wrapper to run the MCP server with proper environment."""

import sys
import os
import logging

# Set up paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S.%f'
)

logger = logging.getLogger(__name__)


def _print_permission_error_help(config_path: str):
    """Print helpful error message for permission issues."""
    print(f"\n❌ ERROR: Permission denied accessing config file: {config_path}", file=sys.stderr)
    print("❌ This usually happens when the file is on Desktop/Documents and Terminal lacks folder access.", file=sys.stderr)
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


try:
    from analytics_mcp.server import run_server

    # Config path is optional - if provided, must exist and be accessible
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        if not os.path.exists(config_path):
            print(f"❌ Config file not found: {config_path}", file=sys.stderr)
            print(f"Usage: {sys.argv[0]} [config_path]", file=sys.stderr)
            print(f"  config_path: Optional OAuth config file (uses ADC if not provided)", file=sys.stderr)
            sys.exit(1)

        # Test file accessibility early
        try:
            with open(config_path, 'r') as f:
                f.read(1)
        except PermissionError:
            _print_permission_error_help(config_path)
            sys.exit(1)
        except Exception as e:
            error_msg = str(e).lower()
            if "operation not permitted" in error_msg or "permission denied" in error_msg:
                _print_permission_error_help(config_path)
                sys.exit(1)
            raise

        logger.info(f"Using OAuth config file: {config_path}")
    else:
        logger.info("Starting MCP server with Application Default Credentials")

    run_server(config_path)

except Exception as e:
    logger.error(f"Server crashed: {e}", exc_info=True)
    sys.exit(1)