# Naming Conventions for CSS

## 1. General Guidelines
- Use lowercase letters for class and ID names.
- Separate words with hyphens (kebab-case) for better readability.
- Avoid using underscores or camelCase.

## 2. Class Naming
- **Component Classes**: Prefix component classes with the component name. For example, `.button`, `.card`, `.modal`.
- **State Classes**: Use a suffix to indicate the state of a component. For example, `.button--active`, `.card--highlighted`.
- **Modifier Classes**: Use a double hyphen to indicate variations. For example, `.button--large`, `.card--bordered`.

## 3. ID Naming
- Use IDs sparingly and only when necessary.
- Follow the same naming conventions as classes, but use a single hash for IDs. For example, `#header`, `#footer`.

## 4. Utility Classes
- Prefix utility classes with `u-` to indicate their purpose. For example, `.u-margin-top`, `.u-padding-small`.
- Keep utility classes generic and reusable across components.

## 5. Responsive Classes
- Use a suffix to indicate responsive behavior. For example, `.grid--mobile`, `.flex--desktop`.

## 6. BEM Methodology
- Consider using the BEM (Block Element Modifier) methodology for larger projects:
  - **Block**: The main component (e.g., `header`, `footer`).
  - **Element**: A part of the block (e.g., `header__logo`, `footer__link`).
  - **Modifier**: A variant of the block or element (e.g., `header--sticky`, `footer__link--active`).

## 7. Avoiding Conflicts
- Use unique prefixes for classes and IDs to avoid conflicts with third-party libraries or frameworks.

## 8. Documentation
- Document naming conventions in your project’s style guide to ensure consistency among team members.