# Contributing to CONSOLEX

Thank you for considering contributing to CONSOLEX!

## Code of Conduct

By participating, you agree to maintain a respectful and inclusive environment.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Include steps to reproduce, expected behavior, and actual behavior
3. Include browser/OS/environment details

### Suggesting Features

1. Describe the feature and its use case
2. Explain how it fits the project's scope

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests: `python manage.py test`
5. Ensure no linting errors
6. Commit with a descriptive message
7. Push and open a Pull Request

## Development Guidelines

- Follow existing code style and conventions
- Use `--cx-*` CSS custom properties for styling
- No hardcoded colors or inline styles
- Templates extend `base.html`, `users/portal_base.html`, or `staff/base_staff.html`
- All new views should include appropriate tests
- Keep functions small and focused
- Use Django's `config()` for environment variables
- Run `python manage.py makemigrations --check --dry-run` before pushing to catch missing migrations
- Install dependencies from `requirements/base.txt` (and `requirements/production.txt` for prod-only packages)

## Project Structure

```
apps/           # Django applications
config/         # Settings and URL configuration
static/         # CSS, JS, images
templates/      # Django templates
media/          # User-uploaded files
requirements/   # base.txt + production.txt (root requirements.txt is a flattened reference)
```

## Commit Messages

Use clear, descriptive commit messages:

- `feat: add tournament registration`
- `fix: correct time slot validation`
- `refactor: extract payment service`
- `docs: update README with deployment steps`
