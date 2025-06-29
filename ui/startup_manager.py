# src/ui/startup_manager.py

import platform
import os
import sys
from pathlib import Path
import subprocess
from PyQt6.QtWidgets import QMessageBox

from utils.debug_logger import get_debug_logger
from utils.debug_decorator import debug_method

debug = get_debug_logger()

class StartupManager:
    """Manages application startup with the operating system"""
    
    def __init__(self, app_name="Task Organizer"):
        self.app_name = app_name
        self.system = platform.system()
        debug.debug(f"Initializing StartupManager for {self.system}")
    
    @debug_method
    def is_startup_enabled(self):
        """Check if the application is set to start with the system"""
        try:
            if self.system == "Windows":
                return self._check_windows_startup()
            elif self.system == "Darwin":  # macOS
                return self._check_macos_startup()
            else:  # Linux
                return self._check_linux_startup()
        except Exception as e:
            debug.error(f"Error checking startup status: {e}")
            return False
    
    @debug_method
    def enable_startup(self):
        """Enable the application to start with the system"""
        try:
            if self.system == "Windows":
                return self._enable_windows_startup()
            elif self.system == "Darwin":  # macOS
                return self._enable_macos_startup()
            else:  # Linux
                return self._enable_linux_startup()
        except Exception as e:
            debug.error(f"Error enabling startup: {e}")
            return False
    
    @debug_method
    def disable_startup(self):
        """Disable the application from starting with the system"""
        try:
            if self.system == "Windows":
                return self._disable_windows_startup()
            elif self.system == "Darwin":  # macOS
                return self._disable_macos_startup()
            else:  # Linux
                return self._disable_linux_startup()
        except Exception as e:
            debug.error(f"Error disabling startup: {e}")
            return False
    
    # Windows Implementation
    @debug_method
    def _check_windows_startup(self):
        """Check Windows registry for startup entry"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return bool(value)
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            debug.error(f"Error checking Windows startup: {e}")
            return False
    
    @debug_method
    def _enable_windows_startup(self):
        """Add entry to Windows registry"""
        try:
            import winreg
            
            # Get the path to the current Python executable and script
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                app_path = sys.executable
            else:
                # Running as Python script
                script_path = os.path.abspath(sys.argv[0])
                app_path = f'"{sys.executable}" "{script_path}"'
            
            debug.debug(f"Adding Windows startup entry: {app_path}")
            
            # IMPORTANT: Only add to registry, don't execute anything
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
            
            debug.debug("Windows startup enabled successfully - registry entry created")
            debug.debug("NOTE: App will start automatically on NEXT login, not immediately")
            return True
        except Exception as e:
            debug.error(f"Error enabling Windows startup: {e}")
            return False
    
    @debug_method
    def _disable_windows_startup(self):
        """Remove entry from Windows registry"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            
            debug.debug("Windows startup disabled successfully")
            return True
        except FileNotFoundError:
            # Entry doesn't exist, which means it's already disabled
            debug.debug("Windows startup entry not found (already disabled)")
            return True
        except Exception as e:
            debug.error(f"Error disabling Windows startup: {e}")
            return False
    
    # macOS Implementation
    @debug_method
    def _check_macos_startup(self):
        """Check macOS launch agents for startup entry"""
        try:
            plist_path = self._get_macos_plist_path()
            return plist_path.exists()
        except Exception as e:
            debug.error(f"Error checking macOS startup: {e}")
            return False
    
    @debug_method
    def _enable_macos_startup(self):
        """Create macOS launch agent plist file"""
        try:
            plist_path = self._get_macos_plist_path()
            
            # Get the path to the current Python executable and script
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                app_path = sys.executable
                program_arguments = [app_path]
            else:
                # Running as Python script
                script_path = os.path.abspath(sys.argv[0])
                program_arguments = [sys.executable, script_path]
            
            debug.debug(f"Creating macOS launch agent: {plist_path}")
            
            # Create the LaunchAgents directory if it doesn't exist
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create the plist content
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.taskorganizer.startup</string>
    <key>ProgramArguments</key>
    <array>
        {''.join(f'<string>{arg}</string>' for arg in program_arguments)}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
            
            # Write the plist file
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # DON'T load the launch agent immediately - just create the file
            # The system will load it automatically on next login
            debug.debug("macOS startup enabled successfully - plist file created")
            debug.debug("NOTE: App will start automatically on NEXT login, not immediately")
            return True
                
        except Exception as e:
            debug.error(f"Error enabling macOS startup: {e}")
            return False
    
    @debug_method
    def _disable_macos_startup(self):
        """Remove macOS launch agent plist file"""
        try:
            plist_path = self._get_macos_plist_path()
            
            if plist_path.exists():
                # Unload the launch agent
                subprocess.run(['launchctl', 'unload', str(plist_path)], 
                             capture_output=True, text=True)
                
                # Remove the plist file
                plist_path.unlink()
                
                debug.debug("macOS startup disabled successfully")
            else:
                debug.debug("macOS launch agent not found (already disabled)")
            
            return True
        except Exception as e:
            debug.error(f"Error disabling macOS startup: {e}")
            return False
    
    @debug_method
    def _get_macos_plist_path(self):
        """Get the path to the macOS launch agent plist file"""
        home = Path.home()
        return home / "Library" / "LaunchAgents" / "com.taskorganizer.startup.plist"
    
    # Linux Implementation
    @debug_method
    def _check_linux_startup(self):
        """Check Linux autostart directory for desktop entry"""
        try:
            desktop_path = self._get_linux_desktop_path()
            return desktop_path.exists()
        except Exception as e:
            debug.error(f"Error checking Linux startup: {e}")
            return False
    
    @debug_method
    def _enable_linux_startup(self):
        """Create Linux autostart desktop entry"""
        try:
            desktop_path = self._get_linux_desktop_path()
            
            # Get the path to the current Python executable and script
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exec_path = sys.executable
            else:
                # Running as Python script
                script_path = os.path.abspath(sys.argv[0])
                exec_path = f"{sys.executable} {script_path}"
            
            debug.debug(f"Creating Linux autostart entry: {desktop_path}")
            
            # Create the autostart directory if it doesn't exist
            desktop_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create the desktop entry content
            desktop_content = f"""[Desktop Entry]
Type=Application
Name={self.app_name}
Comment=Task management application
Exec={exec_path}
Icon=task-organizer
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
            
            # Write the desktop file
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            
            # Make it executable
            os.chmod(desktop_path, 0o755)
            
            debug.debug("Linux startup enabled successfully")
            return True
            
        except Exception as e:
            debug.error(f"Error enabling Linux startup: {e}")
            return False
    
    @debug_method
    def _disable_linux_startup(self):
        """Remove Linux autostart desktop entry"""
        try:
            desktop_path = self._get_linux_desktop_path()
            
            if desktop_path.exists():
                desktop_path.unlink()
                debug.debug("Linux startup disabled successfully")
            else:
                debug.debug("Linux autostart entry not found (already disabled)")
            
            return True
        except Exception as e:
            debug.error(f"Error disabling Linux startup: {e}")
            return False
    
    @debug_method
    def _get_linux_desktop_path(self):
        """Get the path to the Linux autostart desktop file"""
        # Check XDG_CONFIG_HOME first, then fall back to ~/.config
        config_home = os.environ.get('XDG_CONFIG_HOME')
        if config_home:
            config_dir = Path(config_home)
        else:
            config_dir = Path.home() / ".config"
        
        return config_dir / "autostart" / "task-organizer.desktop"
    
    @debug_method
    def toggle_startup(self, enable):
        """Toggle startup on or off with user feedback"""
        if enable:
            success = self.enable_startup()
            if success:
                return True, "Application will start when you log in next time.\n\nNOTE: This won't launch the app immediately - it will only start on your next login."
            else:
                return False, "Failed to enable startup. You may need administrator privileges."
        else:
            success = self.disable_startup()
            if success:
                return True, "Application will no longer start when you log in."
            else:
                return False, "Failed to disable startup."