# Contributing to Frostplay

Thank you for your interest in contributing to Frostplay!

## Code of Conduct

Please be respectful, constructive, and open to feedback when participating in issues and pull requests.

## How to Contribute

### 1. Reporting Bugs
- Check existing [Issues](https://github.com/ma3str0x/Frostplay/issues) before opening a new one.
- Provide clear steps to reproduce the issue, your Windows version, and logs if applicable.

### 2. Suggesting Enhancements
- Open an Issue describing the feature, why it is needed, and how it should behave.

### 3. Pull Requests

1. **Fork and clone the repository:**
   ```powershell
   git clone https://github.com/ma3str0x/Frostplay.git
   cd Frostplay
   ```

2. **Set up the virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Ensure prerequisites are present:**
   Place `mpv-2.dll` and `ffprobe.exe` in the project root directory.

4. **Create a feature branch:**
   ```powershell
   git checkout -b feature/your-feature-name
   ```

5. **Follow code style & conventions:**
   - Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`).
   - Python code must pass formatting, linting, and type checking:
     ```powershell
     ruff check .
     mypy .
     python -m pytest -v
     ```

6. **Submit your Pull Request:**
   - Push to your fork and create a PR targeting `main`.
   - Provide a concise description of your changes and reference any related issues.
