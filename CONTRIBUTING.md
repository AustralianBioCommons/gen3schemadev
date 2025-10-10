# Contributing to Gen3SchemaDev

Thank you for your interest in contributing to Gen3SchemaDev! 🎉

We welcome contributions from the community to make this project even better.

## How to Contribute

1. **Fork the repository**
2. **Create a new branch**
   - Use a descriptive branch name (e.g., `feature/add-rule-validator`, `fix/schema-typo`)
3. **Make your changes**
   - Follow the existing code style and add tests if appropriate.
4. **Commit your changes**
   - Write clear and meaningful commit messages.
5. **Push your branch to your fork**
6. **Open a Pull Request (PR)**
   - Use the PR template below and describe your changes.

## Guidelines

- Make sure your branch is up-to-date with `main`.
- For significant changes, please open an issue first to discuss what you would like to change.
- Update or add documentation as needed.
- Ensure that tests pass (`poetry run pytest`).
- Be respectful and constructive in your code reviews and discussions.

## Local Development

To install dependencies and run tests:

```bash
pip install poetry
poetry install
source $(poetry env info --path)/bin/activate
poetry run pytest
```


## Pull Request (PR) Template

When opening a PR, please copy and fill out the following template:

---

**Description**
> Briefly describe the changes in this PR.

**Related Issues**
> Closes #[issue_number] (if applicable)

**Checklist**
- [ ] I have rebased/merged latest from `main`
- [ ] I have added/updated tests as needed
- [ ] All tests are passing (`poetry run pytest`)
- [ ] I have updated documentation as needed
- [ ] My code follows project code style

**Additional Notes**
> Add anything else reviewers should be aware of.

---

Thank you for contributing! If you have any questions, feel free to open an issue or start a discussion.

---


