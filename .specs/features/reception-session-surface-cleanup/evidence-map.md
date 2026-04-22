# Evidence Map

## Initial Finding

Inline visual debt was found in:

1. [reception_session_featured_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_session_featured_card.html)
2. [reception_session_queue_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_session_queue_card.html)

## Runtime Note

Direct include search did not show these two templates wired into the current `reception_class_grid_board.html`, which currently uses:

1. [reception_class_session_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_class_session_card.html)

This suggests the cleaned files may currently be:

1. residual stock
2. alternate variants for future reuse

## Cleanup Result

1. both templates had `style=` removed
2. the extracted styling moved to [class-grid.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/operations/reception/class-grid.css)
3. `python manage.py check` passed after the extraction
