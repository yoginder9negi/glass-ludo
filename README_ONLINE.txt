GLASS LUDO - ONLINE MULTIPLAYER  (Developed by Yoginder Singh Negi)
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

RESUME / CLOSE SESSION
 If the app or browser closes by accident, just open the game again: a "Welcome back" screen offers
 "Resume" (offline game or online room) or "Close session" to discard it. Online, your seat is kept, so you
 rejoin as the same player and the game replays instantly. Closing the session before the game starts frees
 your seat (if the host closes, the room closes).
 Rooms are saved to ludo_rooms.json next to ludo.py, so on a PC/VPS they even survive a server restart
 (free cloud hosts with a temporary disk lose them on restart).

LOWEST LATENCY (REAL TIME)
 - Game now uses WebSockets (one always-open connection) and your own taps react instantly (dice spins, token moves)
   without waiting for the server.
 - The biggest factor is DISTANCE to the server. Best: a small server in your country.
   Example for India: a VPS in Mumbai/Bangalore (AWS Lightsail Mumbai, DigitalOcean Bangalore, Oracle Cloud Mumbai free tier).
     1. Install Python 3, copy ludo.py to the server, run:  PORT=8000 python3 ludo.py
        (keep it running with:  nohup python3 ludo.py &   or a systemd service)
     2. Open port 8000 in the provider's firewall, share  http://SERVER-IP:8000
        For https (needed for Add-to-Home-screen / install): run on the server
        cloudflared tunnel --url http://localhost:8000   and share the https link it prints.
 - Next best: Render with Region = Singapore. Avoid far regions (USA/Europe).
 - Watch the 🟢 ms badge at the top of the screen: under 150 ms feels real time.

QUIT: the 🚪 Quit button (top-left, during a game) lets any player leave. Offline it returns to the menu.
 Online, the others carry on: the quitter's turns are skipped, the host role passes to someone still playing,
 and if only one player remains that player wins.

MAKE THE WEB VERSION AVAILABLE TO MULTIPLAYER (anyone, any phone/PC browser - nothing to install):
 1. Put ludo.py on a server people can reach (Render.com free / a VPS / your PC + tunnel) - see options A, B, C above.
 2. Open the server's https link, tap "Play Online with Friends", create a room, press "Invite friends".
 3. Friends open the shared link in any browser, enter a name, and join. The host presses Start.

FUN EFFECTS: when a goti is cut, the killer turns into a cartoon hammer that smashes the victim while a cartoon dhol player
 plays a Punjabi dhol and shouts "Wo maara!". When a goti reaches home, a wedding shehnai plays and a cute girl pushes
 the lota (griha pravesh). Voices use the phone's text-to-speech (Hindi voice is used if installed).

GAME FROZE ("X is playing..." and nothing moves)?  Press the 🔄 Sync button (top-left, online games). Every phone rebuilds the game
from the server's log and everyone continues from the same point. The game also heals itself: it detects lost messages, dead
connections, phones waking up from sleep, and phones that disagree about the game, and re-syncs automatically.

SLOW / LATE MOVES: the ping badge (bottom-right) is the round trip to your server. Under 150 ms feels instant.
 A high number (e.g. 400 ms) is distance or a weak connection, not the game. Fix it by: (1) hosting in or near your country
 (India: a VPS in Mumbai/Bangalore, Oracle Cloud free tier Mumbai, Fly.io 'bom', AWS/Google Mumbai), (2) Render region Singapore at least,
 (3) Wi-Fi or strong 4G/5G, no VPN/data saver, (4) an always-on server (free Render sleeps when idle).


HOME-LANE RULE: a token enters its home lane once its player has cut at least one opponent token. If nobody has been cut yet, the token
 skips the lane the first time it passes and goes round the board once more; on the next round it can enter. (No automatic walking home.)
THREE SIXES in a row: turn lost, tokens go back, and a big thumbs-down 👎 falls on the player's start square.
