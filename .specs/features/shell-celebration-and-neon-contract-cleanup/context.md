# Context

The shell was already functionally healthy, but `shell.js` still mixed state control with visual ownership in a few high-authority places:

1. celebration confetti pieces
2. celebration toast dismissal
3. sessions board neon overlay
4. topbar scroll affordance cursor

This was not a production bug, but it kept the shell acting like both conductor and costume designer.
