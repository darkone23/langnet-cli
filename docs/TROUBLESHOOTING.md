# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with langnet-cli.

## 🔍 Quick Diagnosis

### First Steps
```bash
# Check overall system health
langnet-cli verify

# Check specific backend status
curl http://localhost:8888/morphology?word=lupus
curl http://localhost:48080/sktreader/word/agni
whitakers-words lupus
```

## 🚨 Critical Issues

### 1. Duplicate Fields in LanguageEngineConfig
**Problem**: Runtime behavior undefined due to duplicate configuration
```python
# src/langnet/engine/core.py:131-132 (DUPLICATE!)
normalization_pipeline: NormalizationPipeline | None = None
enable_normalization: bool = True
```

**Fix**:
```bash
# Edit the file and remove lines 131-132
nano src/langnet/engine/core.py

# Remove these duplicate lines:
# normalization_pipeline: NormalizationPipeline | None = None  # DELETE
# enable_normalization: bool = True                           # DELETE
```

### 2. Server Not Restarting After Code Changes
**Problem**: Server caches Python modules, changes not taking effect

**Fix**:
```bash
# Clear cache and restart
just cli cache-clear
pkill -f "uvicorn langnet.asgi:app"
uvicorn langnet.asgi:app --host 0.0.0.0 --port 8000 &
```

## 🔧 Backend Service Issues

### Diogenes (Greek/Latin) Not Working

#### Symptoms
```bash
langnet-cli verify
# ❌ Diogenes: Connection refused
curl http://localhost:8888/morphology?word=lupus
# Connection refused
```

#### Solutions
```bash
# 1. Check if diogenes is running
ps aux | grep diogenes

# 2. Start diogenes server
cd /path/to/diogenes
diogenes --server --port 8888 &

# 3. Test connection
curl http://localhost:8888/morphology?word=lupus

# 4. If port 8888 is in use, use different port
diogenes --server --port 8889 &
export DIOGENES_URL=http://localhost:8889
```

#### Common Diogenes Issues
```bash
# Permission issues with diogenes binary
chmod +x diogenes
sudo apt-get install libxml2-dev libxslt1-dev

# Missing Perl modules
cpan install XML::Simple LWP::UserAgent
```

### Sanskrit Heritage Platform Not Working

#### Symptoms
```bash
langnet-cli verify
# ❌ Heritage Platform: Connection refused
curl http://localhost:48080/sktreader/word/agni
# Connection refused
```

#### Solutions
```bash
# 1. Check if heritage platform is running
ps aux | "python3 -m http.server"

# 2. Start the heritage platform
cd /path/to/sanskrit-heritage-platform/webroot
python3 -m http.server 48080 &

# 3. Test connection
curl http://localhost:48080/sktreader/word/agni

# 4. Check if the platform is properly installed
cd /path/to/sanskrit-heritage-platform
./setup.sh
```

#### Heritage Platform Setup Issues
```bash
# Java dependency issues
sudo apt-get install openjdk-11-jdk

# Python dependency issues
pip install -r requirements.txt

# Port conflicts
sudo lsof -i :48080
sudo kill -9 <PID>
```

### Whitaker's Words Not Working

#### Symptoms
```bash
langnet-cli verify
# ❌ Whitaker's Words: Command not found
whitakers-words lupus
# bash: whitakers-words: command not found
```

#### Solutions
```bash
# 1. Check if binary exists
ls -la ~/.local/bin/whitakers-words

# 2. If missing, download and install
wget https://github.com/morphgnt/whitakers-words/releases/download/v1.6.0/whitakers-words_linux_x86_64-1.6.0
chmod +x whitakers-words_linux_x86_64-1.6.0
sudo mv whitakers-words_linux_x86_64-1.6.0 /usr/local/bin/whitakers-words

# 3. Verify installation
whitakers-words lupus

# 4. Add to PATH if needed
echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
source ~/.bashrc
```

## 🐛 Query Issues

### 1. "No results found" for valid words

#### Symptoms
```bash
langnet-cli query lat lupus
# No results found
```

#### Solutions
```bash
# 1. Check backend individually
curl "http://localhost:8888/morphology?word=lupus"

# 2. Try different encodings
langnet-cli query grc *ou=sia  # Greek betacode
langnet-cli query san अग्नि   # Sanskrit Devanagari

# 3. Check for typos
langnet-cli query lat lups    # Typo
langnet-cli query lat lupus   # Correct

# 4. Enable verbose logging
LANGNET_LOG_LEVEL=DEBUG langnet-cli query lat lupus
```

### 2. Encoding/Normalization Issues

#### Symptoms
```bash
# Input not being recognized properly
langnet-cli query san agni     # Works
langnet-cli query san अग्नि   # Doesn't work
```

#### Solutions
```bash
# 1. Check encoding detection
LANGNET_LOG_LEVEL=DEBUG langnet-cli query san अग्नि

# 2. Try different Sanskrit encodings
langnet-cli query san aGfi    # SLP1
langnet-cli query san aG      # Harvard-Kyoto
langnet-cli query san agni    # IAST

# 3. Check normalization pipeline
python3 -c "
from langnet.normalization.core import NormalizationPipeline
pipeline = NormalizationPipeline()
print('Devanagari test:', pipeline.normalize('अग्नि', 'san'))
"
```

### 3. Citation System Issues

#### Symptoms
```bash
# No citations in API response
curl "http://localhost:8000/api?q=l=lat&s=lupus" | jq '.citations'
# null or empty
```

#### Solutions
```bash
# 1. Check Diogenes citations directly
curl "http://localhost:8888/morphology?word=lupus" | grep -o 'perseus:[^"]*'

# 2. Test citation extraction manually
python3 -c "
from langnet.asgi import _extract_citations_from_diogenes_result
import requests
response = requests.get('http://localhost:8888/morphology?word=lupus')
result = _extract_citations_from_diogenes_result(response.json())
print(f'Found {len(result.citations)} citations')
"

# 3. Check server logs for errors
LANGNET_LOG_LEVEL=DEBUG curl "http://localhost:8000/api?q=l=lat&s=lupus"
```

## 📦 Installation Issues

### 1. Devenv Environment Issues

#### Symptoms
```bash
devenv shell
# Error: Failed to create environment
```

#### Solutions
```bash
# 1. Reset devenv environment
rm -rf .devenv
devenv shell

# 2. Check nix installation
which nix
nix --version

# 3. Update nix
nix-channel --update
nix-env -i nix

# 4. Check disk space
df -h
```

### 2. Python Dependency Issues

#### Symptoms
```bash
pip install -e .
# Error: Failed building wheel for ...
```

#### Solutions
```bash
# 1. Use devenv environment
devenv shell langnet-cli -- pip install -e .

# 2. Clear pip cache
devenv shell langnet-cli -- pip cache purge

# 3. Install specific versions
devenv shell langnet-cli -- pip install -r requirements.txt

# 4. Check Python version
python3 --version  # Should be 3.11+
```

### 3. Missing External Dependencies

#### Symptoms
```bash
langnet-cli verify
# ❌ Multiple backends missing
```

#### Solutions
```bash
# Systematic installation script
#!/bin/bash
# install-all-backends.sh

echo "Installing Diogenes..."
git clone https://github.com/pjheslin/diogenes.git
cd diogenes
perl install.pl
cd ..

echo "Installing Heritage Platform..."
git clone https://github.com/sanskrit-coders/sanskrit-heritage-platform.git
cd sanskrit-heritage-platform
./setup.sh
cd ..

echo "Installing Whitaker's Words..."
wget https://github.com/morphgnt/whitakers-words/releases/download/v1.6.0/whitakers-words_linux_x86_64-1.6.0
chmod +x whitakers-words_linux_x86_64-1.6.0
sudo mv whitakers-words_linux_x86_64-1.6.0 /usr/local/bin/whitakers-words

echo "Installation complete!"
```

## 🔍 Performance Issues

### 1. Slow Query Response

#### Symptoms
```bash
time langnet-cli query lat lupus
# Real: 2.345s (should be <1s)
```

#### Solutions
```bash
# 1. Check cache effectiveness
langnet-cli query lat lupus    # First time (slow)
langnet-cli query lat lupus    # Second time (should be fast)

# 2. Clear and rebuild cache
just cli cache-clear
langnet-cli query lat lupus

# 3. Check backend performance
time curl http://localhost:8888/morphology?word=lupus
time curl http://localhost:48080/sktreader/word/agni

# 4. Enable debug logging
LANGNET_LOG_LEVEL=DEBUG time langnet-cli query lat lupus
```

### 2. High Memory Usage

#### Symptoms
```bash
ps aux | grep uvicorn
# High memory usage (>1GB)
```

#### Solutions
```bash
# 1. Restart server
pkill -f uvicorn
uvicorn langnet.asgi:app --host 0.0.0.0 --port 8000 &

# 2. Check for memory leaks
LANGNET_LOG_LEVEL=DEBUG langnet-cli query lat longwordthatcausesissues

# 3. Monitor memory usage
watch -n 1 'ps aux | grep uvicorn | awk "{print \$6}"'
```

## 🌐 Network Issues

### 1. Connection Timeouts

#### Symptoms
```bash
langnet-cli query lat lupus
# Error: Connection timeout to Diogenes backend
```

#### Solutions
```bash
# 1. Check network connectivity
ping localhost
curl http://localhost:8888/morphology?word=lupus

# 2. Check firewall settings
sudo ufw status
sudo ufw allow 8888
sudo ufw allow 48080

# 3. Increase timeout
export DIOGENES_TIMEOUT=30
export HERITAGE_TIMEOUT=30
```

### 2. Proxy/VPN Issues

#### Symptoms
```bash
curl http://localhost:8888/morphology?word=lupus
# Connection refused via proxy
```

#### Solutions
```bash
# 1. Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 2. Bypass proxy for localhost
export NO_PROXY=localhost,127.0.0.1

# 3. Test without proxy
unset HTTP_PROXY HTTPS_PROXY
curl http://localhost:8888/morphology?word=lupus
```

## 📊 Data Issues

### 1. Missing Dictionary Data

#### Symptoms
```bash
langnet-cli query grk λόγος
# Limited results or CLTK downloading
```

#### Solutions
```bash
# 1. Allow CLTK data download (first time only)
# This will take ~500MB and several minutes
langnet-cli query grk λόγος

# 2. Check CLTK data directory
ls -la ~/cltk_data/

# 3. Manually download CLTK data
devenv shell langnet-cli -- python -c "
import cltk
cltk.setup.setup_languages('grc', clone=False)
"
```

### 2. CDSL Dictionary Issues

#### Symptoms
```bash
langnet-cli query san agni
# Error: CDSL dictionary not found
```

#### Solutions
```bash
# 1. Check CDSL data directory
ls -la ~/cdsl_data/

# 2. Download CDSL dictionaries
devenv shell langnet-cli -- python -c "
from langnet.cologne.load_cdsl import load_cdsl
load_cdsl('MW')
"

# 3. Verify CDSL installation
cdsl --version
cdsl list
```

## 🔧 Development Issues

### 1. Import Errors

#### Symptoms
```bash
python3 -m src.langnet.cli query lat lupus
# ModuleNotFoundError: No module named 'src'
```

#### Solutions
```bash
# 1. Use proper Python path
PYTHONPATH=/home/nixos/langnet-tools/langnet-cli/src python3 -m src.langnet.cli query lat lupus

# 2. Use devenv environment
devenv shell langnet-cli -- python3 -m src.langnet.cli query lat lupus

# 3. Install in development mode
devenv shell langnet-cli -- pip install -e .
```

### 2. Test Failures

#### Symptoms
```bash
just test
# Some tests failing
```

#### Solutions
```bash
# 1. Run specific test
python -m pytest tests/test_diogenes_citation_extractor.py -v

# 2. Check test environment
devenv shell langnet-cli -- python -m pytest tests/test_diogenes_citation_extractor.py -v

# 3. Run with coverage
python -m pytest tests/ --cov=src/langnet --cov-report=html
```

## 🆘 Getting Additional Help

### 1. Collect Diagnostic Information
```bash
# Create a diagnostic report
#!/bin/bash
# diagnostic.sh

echo "=== Langnet CLI Diagnostic Report ==="
echo "Date: $(date)"
echo "System: $(uname -a)"
echo "Python: $(python3 --version)"
echo

echo "=== Backend Services ==="
langnet-cli verify
echo

echo "=== Environment Variables ==="
env | grep -E "(LANGNET|DIOGENES|HERITAGE|WHITAKERS)"
echo

echo "=== Disk Space ==="
df -h | grep -E "(Filesystem|/home)"
echo

echo "=== Network Connectivity ==="
ping -c 2 localhost
echo "Diogenes: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8888/morphology?word=test)"
echo "Heritage: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:48080/sktreader/word/test)"
echo

echo "=== Python Packages ==="
pip list | grep -E "(langnet|cltk|requests|structlog)"
```

### 2. Common Error Messages

| Error Message | Solution |
|---------------|----------|
| "Connection refused" | Backend service not running |
| "Command not found" | Binary not installed or not in PATH |
| "No results found" | Check backend connectivity, try different encoding |
| "Cache directory not writable" | Fix permissions: `chmod 755 ~/.local/share/langnet` |
| "Module not found" | Use proper PYTHONPATH or devenv environment |

### 3. When to File a Bug Report

File a GitHub issue if you encounter:
- ❌ **Persistent backend failures** after following troubleshooting steps
- ❌ **Reproducible crashes** with specific queries
- ❌ **Incorrect results** that don't match expected behavior
- ❌ **Documentation errors** or missing setup steps

Include in your report:
- Your operating system and Python version
- Complete error messages and stack traces
- Steps to reproduce the issue
- Expected vs actual behavior
- Diagnostic output from `diagnostic.sh` above

---

*For more information, see [DEVELOPMENT.md](DEVELOPMENT.md) and [ARCHITECTURE.md](ARCHITECTURE.md)*