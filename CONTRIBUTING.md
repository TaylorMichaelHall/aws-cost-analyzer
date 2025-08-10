# Contributing to AWS Cost Analyzer

Thank you for your interest in contributing to the AWS Cost Analyzer! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd aws-cost-analyzer
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Set up development environment**
   ```bash
   uv sync
   cp .env.example .env
   # Edit .env with your AWS profile
   ```

4. **Verify setup**
   ```bash
   ./cost-analysis --fetch --days 7
   ```

## 🛠 Development Workflow

### Code Style

- We use **Black** for Python code formatting
- Run formatter before submitting: `uv run black .`
- Follow Python naming conventions (snake_case for functions/variables, PascalCase for classes)

### Testing Changes

1. **Test with real data** (if possible):
   ```bash
   ./cost-analysis --fetch --days 7
   ```

2. **Test with existing CSV**:
   ```bash
   ./cost-analysis --csv data/sample_data.csv
   ```

3. **Test different scenarios**:
   - Different time ranges (days, weeks, months)
   - Different AWS profiles
   - Both basic and enhanced analysis modes

### Project Structure

```
aws-cost-analyzer/
├── aws_cost_suite.py    # Main analysis engine
├── cost-analysis        # Wrapper script
├── status.py            # Status overview
├── pyproject.toml      # Project configuration
├── .env.example        # Environment template
├── data/               # CSV files and raw data
├── outputs/            # Reports and visualizations
└── scripts/            # Additional tools
```

## 📝 Making Changes

### Types of Contributions

1. **Bug Fixes**: Fix issues in analysis logic or visualizations
2. **Features**: Add new analysis capabilities or visualizations
3. **Documentation**: Improve README, comments, or help text
4. **Performance**: Optimize code for speed or memory usage

### Submission Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, commented code
   - Update documentation if needed
   - Test thoroughly

3. **Format code**
   ```bash
   uv run black .
   ```

4. **Commit with clear messages**
   ```bash
   git add .
   git commit -m "Add: brief description of changes"
   ```

5. **Submit a pull request**
   - Describe what the change does
   - Include any testing you performed
   - Reference any related issues

## 🔍 Code Review Guidelines

### For Contributors
- Keep changes focused and atomic
- Write clear commit messages
- Include comments for complex logic
- Update documentation for user-facing changes

### For Reviewers
- Focus on functionality and maintainability
- Suggest improvements constructively
- Test changes if possible
- Verify documentation is updated

## 🐛 Bug Reports

When reporting bugs, include:

1. **Steps to reproduce**
2. **Expected behavior**
3. **Actual behavior**
4. **Environment details**:
   - Operating system
   - Python version (`python --version`)
   - uv version (`uv --version`)
   - AWS CLI version (`aws --version`)

## 💡 Feature Requests

For new features, provide:

1. **Use case description**
2. **Proposed solution** (if you have one)
3. **Alternative approaches considered**
4. **Impact assessment** (who benefits, complexity)

## 🔒 Security Considerations

- **Never commit credentials** (AWS keys, tokens, etc.)
- **Avoid logging sensitive data** (account IDs, specific costs)
- **Use environment variables** for configuration
- **Sanitize user inputs** in new features

## 📚 Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [AWS Cost Explorer API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-explorer-api.html)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Matplotlib Documentation](https://matplotlib.org/stable/users/index.html)

## 🤝 Code of Conduct

- Be respectful and constructive in discussions
- Focus on the code and technical aspects
- Help create a welcoming environment for all contributors
- Report any inappropriate behavior to the project maintainers

## 📞 Getting Help

- Open an issue for questions
- Check existing issues and documentation first
- Provide clear context when asking questions

Thank you for contributing to make AWS cost analysis better for everyone! 🎉