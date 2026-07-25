# NetAdminPy

**Enterprise-grade network administration and monitoring platform** built with Python and PySide6.

## Features

- **Authentication & RBAC**: Secure login with role-based access control (Administrator, Network Operator, Security Analyst, Viewer)
- **Network Discovery**: Scan and discover devices on your network
- **Device Monitoring**: Real-time monitoring of network device status
- **Inventory Management**: Track and manage network devices
- **Configuration Backup**: Automated SSH-based device configuration backups
- **Reporting**: Generate comprehensive network reports
- **Audit Logging**: Complete audit trail of all actions
- **AI Analysis**: Intelligent network insights (extensible)

## Quick Start

### Prerequisites

- Python 3.14+
- Windows / Linux / macOS

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/NetAdminPy.git
cd NetAdminPy

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows
source .venv/bin/activate     # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python app.py
```

**Default admin credentials:**
- Username: `admin`
- Password: (auto-generated on first run, check console output)

To set a custom admin password:
```bash
$env:NETADMINPY_ADMIN_PASSWORD="YourSecurePassword123!"
python app.py
```

## Architecture

```
app/
├── auth/                  # Authentication services
├── authorization/         # Permission-based access control
├── models/               # Domain models
├── services/             # Business logic services
├── repositories/         # Data access layer
├── database/            # SQLite persistence
├── core/                # Network utilities (scanner, monitor, SSH)
├── gui/                 # PySide6 user interface
└── tests/               # Unit and integration tests
```

## Security

- Passwords: PBKDF2-HMAC-SHA256 with 200,000 iterations
- Sessions: Time-limited and invalidation on logout
- Account lockout: Automatic after 5 failed login attempts
- Audit logging: All sensitive actions logged to database

## Development

### Run Tests

```bash
python -m unittest discover -s tests -v
```

### Contributing

1. Create a feature branch (`git checkout -b feature/amazing-feature`)
2. Commit changes (`git commit -m 'Add amazing feature'`)
3. Push to branch (`git push origin feature/amazing-feature`)
4. Open a Pull Request

## License

© 2026 IndusRocker Technologies. All rights reserved.

## Support

For issues, feature requests, or security vulnerabilities, please open an issue on GitHub.
