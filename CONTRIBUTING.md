# Contributing to Linkwarden Alfred Workflow

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** from `main`
4. **Make your changes**
5. **Test thoroughly**
6. **Submit a pull request**

## Development Environment

### Prerequisites

- macOS with Alfred 5+ (Powerpack required)
- Python 3.7+
- Access to a Linkwarden instance
- Valid Linkwarden API token

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/joscandreu/linkwarden-alfred-workflow.git
   cd linkwarden-alfred-workflow
   ```

2. Configure your test environment:
   - Set up `LW_API_URL` and `LW_API_TOKEN` environment variables
   - Import the workflow into Alfred for testing

3. Test the workflow:
   ```bash
   # Test API connection
   python3 linkwarden_api.py

   # Test search functionality
   python3 linkwarden_search.py "test query"
   ```

## Code Style

- Follow PEP 8 Python style guidelines
- Use descriptive variable and function names
- Add docstrings to all public functions and classes
- Include type hints where appropriate
- Keep functions focused and modular

### Documentation

- Document all new features in the README
- Add inline comments for complex logic
- Update the changelog for significant changes
- Include examples for new functionality

## Testing

### Manual Testing

1. **Search functionality**:
   - Test various search queries
   - Verify tag and collection filtering
   - Check visual feedback for matched filters

2. **Collection browsing**:
   - Navigate through collection hierarchy
   - Test collection filtering
   - Verify link opening functionality

3. **Link saving**:
   - Test URL normalization
   - Verify tag and collection assignment
   - Check notification display

### Edge Cases

- Empty search results
- Invalid URLs
- Missing API credentials
- Network connectivity issues
- API rate limiting

## Known Issues

### Linkwarden API Bug

The workflow implements a two-step save process to work around a known Linkwarden API bug where `collectionId` parameters are ignored in POST requests. When modifying the save functionality:

1. **Do not remove** the two-step process
2. **Test thoroughly** with collection assignment
3. **Document any changes** to the workaround

### Error Handling

- Always provide user-friendly error messages
- Log detailed errors to stderr for debugging
- Handle API timeouts gracefully
- Validate user input appropriately

## Submitting Changes

### Pull Request Process

1. **Update documentation** for any new features
2. **Test on different Linkwarden versions** if possible
3. **Ensure no breaking changes** unless absolutely necessary
4. **Write clear commit messages**
5. **Reference any related issues**

### Commit Message Format

```
type(scope): brief description

Longer description if needed

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tested manually
- [ ] No breaking changes
- [ ] Documentation updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
```

## Questions and Support

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and general discussion
- **Documentation**: Check the README and inline code documentation

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment
- Follow GitHub's Community Guidelines

Thank you for contributing to the Linkwarden Alfred Workflow!