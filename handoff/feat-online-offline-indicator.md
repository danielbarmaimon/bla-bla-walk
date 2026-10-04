# Online/offline mode indicator

## State
Implemented on `feat/online-offline-indicator`. The header shows a symbol and text for the selected query mode: Online, Offline, or Example. This reflects the app's selected data mode, not live network reachability.

## Done
Added accessible labeled status to the header and distinct mark styling for the three supported modes. No shared data contract changed.

## Next
Review the indicator in the browser in `/?mode=online`, `/?mode=offline`, and `/?mode=fixture`; adjust compact header spacing if needed.
