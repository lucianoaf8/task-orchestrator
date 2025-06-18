import subprocess
import sys
from pathlib import Path

# Allow scripts to import project modules when run directly
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
import socket
import platform
import dns.resolver
import dns.exception

def check_vpn_connection():
    """Check if VPN is connected using cross-platform detection"""
    try:
        system = platform.system()
        
        # Method 1: Check for VPN interface
        if system == "Windows":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            vpn_indicators = ['VPN', 'TAP', 'Cisco AnyConnect', 'OpenVPN']
        elif system == "Darwin":  # macOS
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            vpn_indicators = ['utun', 'ppp', 'tun']
        else:  # Linux
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
            vpn_indicators = ['tun', 'ppp', 'vpn']
        
        if any(indicator in result.stdout for indicator in vpn_indicators):
            print(f"VPN interface detected on {system}")
            return True
            
        # Method 2: Try to reach internal IP ranges
        internal_ips = [
            '10.0.0.1',      # Common internal gateway
            '192.168.1.1',   # Common home router
            '172.16.0.1'     # Private network range
        ]
        
        for ip in internal_ips:
            try:
                sock = socket.create_connection((ip, 80), timeout=5)
                sock.close()
                print(f"Successfully connected to internal IP: {ip}")
                return True
            except (OSError, socket.timeout, socket.error):
                continue
                
        # Method 3: Check for specific company domain resolution
        # Replace with your company's internal domain
        try:
            dns.resolver.resolve("internal.company.com", 'A')
            print(f"Internal domain internal.company.com resolved")
            return True
        except dns.exception.DNSException:
            pass
                
        print("VPN connection not detected")
        return False
        
    except Exception as e:
        print(f"Error checking VPN: {e}")
        return False

if __name__ == "__main__":
    if check_vpn_connection():
        sys.exit(0)
    else:
        sys.exit(1)