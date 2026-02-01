# Getting Started with Langnet CLI

This guide will help you get started with langnet-cli, a classical language education tool for Latin, Greek, and Sanskrit.

## 🚀 Quick Installation

### Prerequisites
- **Python 3.11+** with pip
- **Git** for cloning the repository
- **Three external services** (see below)

### 1. Clone the Repository
```bash
git clone https://github.com/sst/langnet-cli.git
cd langnet-cli
```

### 2. Enter Development Environment
```bash
devenv shell
```
This automatically sets up the Python environment with all required dependencies.

### 3. Install External Dependencies

#### Sanskrit Heritage Platform
```bash
# Install the platform
git clone https://github.com/sanskrit-coders/sanskrit-heritage-platform.git
cd sanskrit-heritage-platform
./setup.sh

# Start the server
cd webroot
python3 -m http.server 48080 &
```

#### Diogenes (Greek/Latin)
```bash
# Install diogenes
git clone https://github.com/pjheslin/diogenes.git
cd diogenes
perl install.pl

# Start the server
diogenes --server --port 8888 &
```

#### Whitaker's Words (Latin)
```bash
# Download prebuilt binary
wget https://github.com/morphgnt/whitakers-words/releases/download/v1.6.0/whitakers-words_linux_x86_64-1.6.0
chmod +x whitakers-words_linux_x86_64-1.6.0
sudo mv whitakers-words_linux_x86_64-1.6.0 /usr/local/bin/whitakers-words
```

### 4. Verify Installation
```bash
# Check all backends are working
langnet-cli verify
```

You should see:
```
✅ Whitaker's Words: Available
✅ Diogenes: Available  
✅ Heritage Platform: Available
✅ CLTK: Available
✅ CDSL: Available
```

## 🎯 First Queries

### Basic Language Queries
```bash
# Latin
langnet-cli query lat lupus        # wolf
langnet-cli query lat amor         # love
langnet-cli query lat arma         # weapons

# Greek  
langnet-cli query grc λόγος      # word
langnet-cli query grc ἄνθρωπος   # human
langnet-cli query grc οὐρανός    # sky/heaven

# Sanskrit
langnet-cli query san agni        # fire
langnet-cli query san deva        # god
langnet-cli query san dharma      # duty/law
```

### Advanced Features
```bash
# Get detailed analysis with morphology
langnet-cli query lat lupus --output detailed

# Search with specific lemmas
langnet-cli query grk λόγος --lemma

# View citation context
langnet-cli query lat lupus --citations

# Use different output formats
langnet-cli query san agni --output json
langnet-cli query lat lupus --output yaml
```

## 🏗️ Start the API Server

For programmatic access:
```bash
# Start the server
uvicorn-run

# Test the API
curl "http://localhost:8000/api/q?l=lat&s=lupus"
```

## 📚 Next Steps

### For Users
- Explore the [examples/](../examples/) directory for more usage patterns
- Read [PEDAGOGY.md](PEDAGOGY.md) to understand the educational approach
- Try the [citation commands](#citation-commands) below

### For Developers
- Follow [DEVELOPMENT.md](DEVELOPMENT.md) for setup and workflow
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system design
- Check [ROADMAP.md](ROADMAP.md) for current development status

### Citation Commands (New!)
```bash
# Explain citation abbreviations
langnet-cli citation explain "Hom."
langnet-cli citation explain "Cic."
langnet-cli citation explain "L&S"

# List all citations for a word
langnet-cli citation list lat lupus
langnet-cli citation list grk λόγος
langnet-cli citation list san agni
```

## 🔧 Common Issues

### Backend Services Not Starting
```bash
# Check if ports are available
netstat -tulpn | grep :48080  # Heritage Platform
netstat -tulpn | grep :8888    # Diogenes
netstat -tulpn | grep :5000    # Whitaker's Words

# If ports are in use, change them:
# Heritage Platform: edit webroot/server.js, change port
# Diogenes: run with different port
diogenes --server --port 8889 &
```

### Python Environment Issues
```bash
# Reset the development environment
rm -rf .devenv
devenv shell

# Reinstall dependencies
devenv shell langnet-cli -- pip install -e .
```

### Dictionary Data Missing
```bash
# CLTK will download data automatically on first use
# This may take 500MB+ and several minutes

# CDSL dictionaries download automatically
# Check in ~/cdsl_data/
```

## 🎓 Understanding the Output

### Basic Query Response
```
lupus, i, m.
wolf; Sanskr. vrika, and our wolf, a wolf.

Citations:
  Verg. E. 2, 63: torva leaena lupum sequitur, lupus ipse capellam
  Plin. 10, 63, 88: lupus, sacred to Mars
  Hor. C. 1, 17, 9: lupus femina for lupa, a she-wolf
```

### Morphology Breakdown
- **Part of Speech**: `m.` = masculine
- **Case/Number**: `i` = nominative singular
- **Definition**: Dictionary headword and related terms
- **Citations**: Classical usage examples with CTS URNs
- **Morphology**: Grammatical analysis (Foster functional grammar)

## 🔄 Updating the System

### Pull latest changes
```bash
git pull
devenv shell langnet-cli -- pip install -e .
```

### Restart services
```bash
# Restart all backend services
pkill -f "diogenes --server"
pkill -f "python3 -m http.server 48080"
devenv shell langnet-cli -- diogenes --server --port 8888 &
cd sanskrit-heritage-platform/webroot && python3 -m http.server 48080 &
```

## 🆘 Need Help?

1. **Check this guide** for common setup issues
2. **Run `langnet-cli verify`** to diagnose backend problems
3. **Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for more solutions
4. **Check [ARCHITECTURE.md](ARCHITECTURE.md)** for technical details
5. **Open an issue** on GitHub with your error messages

---

*Happy classical language learning! 📚🏛️*  
*Last Updated: February 2, 2026*