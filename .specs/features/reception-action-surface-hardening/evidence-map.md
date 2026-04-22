# Evidence Map

## T1 Behavior and Debt Map

The live reception payment card at:

1. [reception_payment_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_payment_card.html)

originally mixed:

1. inline style on the primary actions row
2. inline style on blocked WhatsApp states
3. inline `onmouseover` and `onmouseout`
4. inline `onclick` with `fetch(...)`
5. embedded WhatsApp message copy inside the HTML attribute

## T2 Extraction Decision

The extraction strategy was locked as:

1. keep payment submit and update submit as normal form submits
2. move the WhatsApp launch behavior to a dedicated JS asset
3. use `data-*` hooks for communication URL, student ID, payment ID, phone, and message inputs
4. move blocked-state and action-row styling to the reception payment CSS owner

## T3 Runtime Extraction Result

The runtime template now:

1. uses `data-action="launch-reception-whatsapp"` instead of inline `onclick`
2. uses route tags for both payment action and communication action
3. carries only declarative `data-*` metadata for the WhatsApp path

The extracted behavior now lives in:

1. [reception-payment-card.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/operations/reception-payment-card.js)

## T4 Visual Extraction Result

The dominant inline visual debt was moved into:

1. [payment.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/operations/reception/payment.css)

The new CSS owns:

1. primary action row layout
2. WhatsApp slot alignment
3. blocked-state hint presentation
4. small-screen stacking behavior

## T5 Validation

Validation after extraction:

1. [reception_payment_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_payment_card.html) is clean for:
   - `style=`
   - `onclick=`
   - `onmouseover=`
   - `onmouseout=`
   - inline `fetch(`
2. [reception.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/reception.html) now loads the dedicated JS asset
3. `python manage.py check` passed

## T5 Conclusion

The operational desk flow stayed intact while the template stopped being the place where:

1. style lived
2. network logic lived
3. WhatsApp copy lived

In simple terms:

1. the counter still works
2. but the wires are no longer exposed on top of the desk
