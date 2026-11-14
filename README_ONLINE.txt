GLASS LUDO - ONLINE MULTIPLAYER  (Prepared by Yoginder Singh Negi)
===================================================================
HOW PLAYERS JOIN
 1. Host opens the game > "Play Online with Friends" > type name > "Create room".
 2. A 4-letter ROOM CODE appears. Tap "Invite friends" (share on WhatsApp etc.) or "Copy link".
 3. Friends open the link (or open the game, tap Play Online, type name + code, Join).
 4. When 2-4 players are in the lobby, the host taps "Start game".
 5. Each player taps the dice / their goti only on their own turn. Dice are rolled by the server (fair).
 If someone refreshes or loses signal, they just reopen the link and rejoin their seat automatically.
 If a player leaves for good, the host gets a "Skip" button on that player's turn.

THE GAME MUST RUN ON A COMPUTER/SERVER THAT EVERYONE CAN REACH. Choose one:

A) SAME WI-FI (family at home) - easiest
   python ludo.py
   Friends open the "Same Wi-Fi friends" address printed in the window (http://192.168.x.x:8000).

B) FRIENDS ANYWHERE, from your own PC (free, temporary link)
   1. Run:  python ludo.py
   2. In a second window run ONE of:
        cloudflared tunnel --url http://localhost:8000      (Cloudflare, no signup)
        ngrok http 8000                                       (ngrok, free account)
   3. It prints an https:// link. Open it yourself, create the room and share the invite.
   (Your PC must stay on while playing.)

C) ALWAYS-ON FREE HOSTING (e.g. Render.com) - no PC needed
   1. Put these files in a GitHub repository (ludo.py, requirements.txt, render.yaml).
   2. On render.com: New > Web Service > connect the repo.
      Runtime: Python.  Start command: python ludo.py   (Free instance)
   2b. IMPORTANT FOR SPEED: choose the Region nearest to your players (for India choose Singapore).
       A far region (e.g. USA) makes every move arrive late. The region cannot be changed later.
   3. After deploy you get https://your-name.onrender.com - that is your permanent game link.
   Notes: free instances sleep when idle (first open can take ~1 minute). Rooms are kept in memory, so they
   disappear if the server restarts. Any host that can run "python ludo.py" and gives a PORT works
   (Railway, Fly.io, Koyeb, a VPS...).

INSTALL AS AN APP: open the hosted https link in Chrome on Android > menu > "Add to Home screen".

GAME OPTIONS: choose how many goti must reach home to win (1-4); press 🏁 Finish to end a game early (online: host only).
