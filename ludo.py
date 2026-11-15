#!/usr/bin/env python3
"""
GLASS LUDO v2 - web based, pure Python (no installs needed).
Run:  python ludo.py
 - Computer: http://localhost:8000
 - Mobile  : open the "On your mobile" link printed in the terminal (same Wi-Fi)
ONLINE MODE: "Play Online" -> Create room -> share the invite link/code. Friends open the link, enter a name and join.
  Host presses Start. Works on same Wi-Fi, or over the internet via a tunnel / free hosting (see README_ONLINE.txt).
Rules
 * Roll 6 to bring a token out. 6 / cutting a goti / reaching home = extra turn.
 * 3 sixes in a row = turn lost, all tokens go back to where they were.
 * A token can NOT enter home until its player has cut at least one opponent
   token. Until then it skips the home lane and keeps circling the board.
 * Exact number needed to reach the final home.
"""
import http.server, socketserver, threading, webbrowser, socket
import json, random, queue, time, os, base64, hashlib, struct
from urllib.parse import urlparse, parse_qs

HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#1b0b3a">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-192.png">
<title>Glass Ludo</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;-webkit-user-select:none;user-select:none}
html,body{margin:0;height:100%;font-family:'Segoe UI',system-ui,sans-serif;color:#fff;overflow:hidden;touch-action:manipulation;overscroll-behavior:none}
body{background:linear-gradient(135deg,#1b0b3a,#0b2a5b,#3a0b4f,#0b4a4a);background-size:400% 400%;animation:bg 18s ease infinite;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
@keyframes bg{50%{background-position:100% 100%}}
.blob{position:fixed;border-radius:50%;filter:blur(60px);opacity:.5;z-index:0;animation:fl 12s ease-in-out infinite alternate;pointer-events:none}
.b1{width:320px;height:320px;background:#ff4d6d;top:-80px;left:-80px}
.b2{width:300px;height:300px;background:#2de08a;bottom:-60px;right:-60px;animation-delay:-4s}
.b3{width:260px;height:260px;background:#ffd23f;top:40%;right:-100px;animation-delay:-7s}
.b4{width:280px;height:280px;background:#4dabff;bottom:10%;left:-100px;animation-delay:-2s}
@keyframes fl{to{transform:translate(60px,-50px) scale(1.2)}}
h1{margin:0;z-index:1;font-size:clamp(16px,3.2vw,26px);letter-spacing:3px;background:linear-gradient(90deg,#ff4d6d,#ffd23f,#2de08a,#4dabff);-webkit-background-clip:text;background-clip:text;color:transparent}
.glass{background:rgba(255,255,255,.12);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border:1px solid rgba(255,255,255,.35);box-shadow:0 10px 40px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.5)}
#board{--bs:min(98vw,calc(100vh - 212px),760px);--bs:min(98vw,calc(100dvh - 212px),760px);position:relative;width:var(--bs);height:var(--bs);border-radius:20px;z-index:1;overflow:hidden;touch-action:manipulation}
#grid{position:absolute;inset:0;display:grid}
.c{margin:.6px;border-radius:24%;background:linear-gradient(145deg,#fff,#e7ecff);border:1px solid #fff;box-shadow:0 1px 3px #0004,inset 0 -2px 4px #0000001a;display:flex;align-items:center;justify-content:center;font-size:calc(var(--bs)/24);color:#ff9d00;font-weight:700}
.c.col{color:#fff;text-shadow:0 1px 3px #0006}
.yard{margin:0;border-radius:16px;border:1px solid rgba(255,255,255,.6)}
.yi{border-radius:16px;background:rgba(255,255,255,.35);box-shadow:inset 0 0 18px #fff9}
#ctr{margin:0;border-radius:8px;background:conic-gradient(from -45deg,#2de08a 0 90deg,#ffd23f 90deg 180deg,#4dabff 180deg 270deg,#ff4d6d 270deg 360deg);box-shadow:inset 0 0 25px #fff8;border:1px solid #fff9}
.tk{position:absolute;border-radius:50%;pointer-events:none;transform:translate(calc(-50% + var(--ox,0%)),calc(-50% + var(--oy,0%)));transition:left var(--tt,.07s) linear,top var(--tt,.07s) linear;z-index:5;border:2px solid #fff;box-shadow:0 4px 8px #0007,inset -3px -4px 8px #0006,inset 3px 3px 6px #fffa;will-change:left,top}
.tk::after{content:"";position:absolute;left:22%;top:14%;width:32%;height:22%;border-radius:50%;background:#fffc;filter:blur(1px)}
.tk.can{z-index:9;animation:hop .5s ease-in-out infinite;box-shadow:0 0 0 3px #fff,0 0 18px 7px currentColor}
@keyframes hop{50%{transform:translate(calc(-50% + var(--ox,0%)),calc(-80% + var(--oy,0%)))}}
#ui{z-index:1;display:flex;align-items:center;gap:12px;padding:8px 14px;border-radius:22px;width:min(96vw,430px);height:110px;flex:none}
@property --pc{syntax:'<color>';inherits:true;initial-value:#ff7ae0}
@property --pd{syntax:'<color>';inherits:true;initial-value:#7a2cff}
#scene{--pc:#ff7ae0;--pd:#7a2cff;transition:--pc .22s,--pd .22s;width:88px;height:88px;perspective:520px;cursor:pointer;touch-action:manipulation;padding:0;filter:drop-shadow(0 12px 10px #0009)}
#cube{position:relative;width:100%;height:100%;transform-style:preserve-3d;transition:transform 1s cubic-bezier(.2,.8,.2,1)}
.f{position:absolute;width:88px;height:88px;border-radius:20px;overflow:hidden;background:radial-gradient(circle at 28% 22%,#fff 0,var(--pc) 42%,var(--pd) 100%);display:grid;grid-template:repeat(3,1fr)/repeat(3,1fr);padding:13px;box-shadow:inset 0 0 16px #fffa,inset 0 0 28px var(--pd),0 0 14px var(--pc);border:2px solid #ffffffcc}
.f::before{content:"";position:absolute;inset:0;background:linear-gradient(120deg,rgba(255,255,255,.65),transparent 42%,transparent 70%,rgba(255,255,255,.25))}
.f i{width:18px;height:18px;border-radius:50%;margin:auto;background:radial-gradient(circle at 35% 30%,#8a86b8 0,#1a1033 55%,#000 100%);box-shadow:0 0 0 2px #fff8,0 0 8px #fff9,inset -1px -1px 2px #0008}
#scene.wait{animation:bob 1.1s ease-in-out infinite}
@keyframes bob{0%,100%{filter:drop-shadow(0 0 6px var(--pc)) drop-shadow(0 12px 10px #0009)}50%{filter:drop-shadow(0 0 24px var(--pc)) drop-shadow(0 12px 10px #0009)}}
#scene.rolling{animation:toss 1s ease-out}
@keyframes toss{40%{transform:translateY(-34px) scale(1.3)}100%{transform:none}}
#scene.six{animation:shake .7s}
#scene.sad{animation:sad 1.1s}
@keyframes sad{15%{transform:rotate(-14deg) translateY(8px)}35%{transform:rotate(10deg) translateY(10px)}55%{transform:rotate(-6deg) translateY(8px)}100%{transform:none}}
#scene.six #cube{filter:drop-shadow(0 0 20px #ffd23f) drop-shadow(0 0 44px #ff4dd8)}
@keyframes shake{20%{transform:scale(1.5) rotate(-10deg)}40%{transform:scale(1.5) rotate(10deg)}60%{transform:scale(1.4) rotate(-6deg)}100%{transform:scale(1)}}
#st{flex:1;min-width:0;height:68px;overflow:hidden;display:flex;flex-direction:column;justify-content:center;font-size:13px;font-weight:600;line-height:1.45;text-shadow:0 2px 6px #0008}
#st b{padding:2px 10px;border-radius:12px;color:#111}
#st small{opacity:.9;font-weight:500}
#stamp{z-index:1;font-size:11px;letter-spacing:1.2px;font-weight:600;padding:3px 14px;border-radius:14px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.4);text-shadow:0 0 8px #ff7ae0,0 1px 3px #0008;box-shadow:0 0 12px rgba(255,122,224,.35)}
.by{font-size:12px;letter-spacing:1px;margin:2px 0 8px;text-shadow:0 0 8px #ff7ae0}
button{font:inherit;color:#fff;border:1px solid #fff8;background:rgba(255,255,255,.2);border-radius:14px;padding:10px 16px;cursor:pointer;touch-action:manipulation}
#toast{position:fixed;top:12%;left:50%;transform:translateX(-50%) scale(.5);font-size:clamp(24px,7vw,48px);font-weight:900;z-index:50;pointer-events:none;opacity:0;text-shadow:0 0 20px #f0f,0 0 40px #ff0;white-space:nowrap}
#toast.show{animation:ts 1.5s}
@keyframes ts{15%{opacity:1;transform:translateX(-50%) scale(1.15)}80%{opacity:1;transform:translateX(-50%) scale(1)}100%{opacity:0;transform:translateX(-50%) scale(1.3)}}
.ov{position:fixed;inset:0;z-index:30;display:flex;align-items:center;justify-content:center;background:rgba(10,0,30,.5);backdrop-filter:blur(6px)}
.ov .glass{padding:24px;border-radius:26px;text-align:center;max-width:92vw}
.row{display:flex;align-items:center;justify-content:space-between;gap:14px;margin:10px 0}
.dot{display:inline-block;width:18px;height:18px;border-radius:50%;margin-right:8px;vertical-align:middle;box-shadow:0 0 10px currentColor}
select{font:inherit;color:#fff;background:rgba(255,255,255,.2);border:1px solid #fff8;border-radius:10px;padding:6px}
select option{color:#000}
#go{font-size:18px;margin-top:8px;background:linear-gradient(90deg,#ff4d6d99,#4dabff99)}
.hide{display:none!important}
input{font:inherit;color:#fff;background:rgba(255,255,255,.2);border:1px solid #fff8;border-radius:12px;padding:10px;width:100%;text-align:center;outline:none}
input::placeholder{color:#ffffffaa}
#rcode{width:130px;letter-spacing:4px;text-transform:uppercase}
#rc{font-size:40px;font-weight:900;letter-spacing:8px;text-shadow:0 0 14px #ff7ae0}
#skip{padding:8px 10px;font-size:13px}
#tl{position:fixed;top:8px;left:8px;z-index:6;display:flex;gap:6px}
#tl button{padding:5px 10px;font-size:12px;background:rgba(255,255,255,.18)}
.toon{position:fixed;z-index:28;pointer-events:none;width:132px;opacity:0;transition:transform .4s cubic-bezier(.2,1.4,.4,1),opacity .25s;bottom:8px}
#toonL{left:4px;transform:translateX(-170%)}
#toonR{right:4px;transform:translateX(170%)}
.toon.show{opacity:1;transform:none}
.toon .bub{position:absolute;top:-24px;left:50%;transform:translateX(-50%);white-space:nowrap;font-weight:800;font-size:13px;background:#fff;color:#b3122a;padding:3px 10px;border-radius:12px;box-shadow:0 2px 8px #0007}
.toon svg{width:100%;height:auto;filter:drop-shadow(0 4px 6px #0008)}
.dh{animation:dbob .3s ease-in-out infinite alternate}@keyframes dbob{to{transform:translateY(-4px)}}
.s1{transform-origin:42px 84px;animation:sh .28s ease-in-out infinite alternate}
.s2{transform-origin:78px 84px;animation:sh .28s ease-in-out infinite alternate-reverse}
@keyframes sh{from{transform:rotate(-14deg)}to{transform:rotate(10deg)}}
.ft{transform-origin:74px 94px;animation:push 1.1s ease-in-out infinite alternate}
@keyframes push{to{transform:rotate(-26deg)}}
.lt{transform-origin:115px 117px;animation:tipl 1.2s ease-out .35s infinite alternate}
@keyframes tipl{to{transform:translateX(9px) rotate(26deg)}}
.rc{animation:rice 1.2s ease-in .5s infinite}
@keyframes rice{0%{transform:translate(0,0);opacity:1}100%{transform:translate(var(--dx,8px),20px);opacity:0}}
#tools{position:fixed;top:8px;right:8px;z-index:6;display:flex;gap:6px}
#tools button{padding:5px 10px;font-size:12px;background:rgba(255,255,255,.18)}
#net{position:fixed;bottom:6px;right:8px;font-size:11px;z-index:6;padding:2px 9px;border-radius:10px;background:rgba(0,0,0,.4)}
body.lite{animation:none;background:linear-gradient(135deg,#1b0b3a,#0b2a5b,#3a0b4f)}
body.lite .blob{display:none}
body.lite .glass,body.lite .ov{backdrop-filter:none;-webkit-backdrop-filter:none}
body.lite .glass{background:rgba(50,30,110,.6)}
body.lite #scene,body.lite #cube,body.lite #scene.wait,body.lite #scene.six #cube{filter:none!important}
body.lite #scene.wait{animation:none}
body.lite .tk{box-shadow:0 2px 4px #0008}
body.lite .tk.can{box-shadow:0 0 0 3px #fff}
body.lite .c,body.lite .yard,body.lite .yi,body.lite #ctr{box-shadow:none}
body.lite .f{box-shadow:inset 0 0 8px #fff8}
#pick{display:grid;grid-template:repeat(2,52px)/repeat(2,64px);gap:8px;justify-content:center;margin:6px 0 10px}
#pick button{padding:0;color:#111;font-weight:800}
#presets{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin:6px 0}
#presets button{padding:6px 10px;font-size:12px}

/* --- dhol boy that appears when a goti leaves the yard --- */
.dm{position:absolute;z-index:13;pointer-events:none;transform:translate(-50%,-50%) scale(0);opacity:0;transition:transform .5s cubic-bezier(.2,1.6,.4,1),opacity .3s}
.dm.show{transform:translate(-50%,-50%) scale(1);opacity:1}
.dm svg{width:100%;height:auto;display:block;overflow:visible;filter:drop-shadow(0 3px 4px #0009)}
.dm:not(.show) svg *{animation-play-state:paused}
body.lite .dm svg{filter:none}
.dm-bd{animation:dmbob .26s ease-in-out infinite alternate}
@keyframes dmbob{from{transform:translateY(0)}to{transform:translateY(-3px)}}
.dm-l{transform-origin:44px 128px;animation:dml .26s ease-in-out infinite alternate}
.dm-r{transform-origin:152px 112px;animation:dml .26s ease-in-out infinite alternate-reverse}
@keyframes dml{from{transform:rotate(-16deg)}to{transform:rotate(12deg)}}
.dm-hd{transform-origin:98px 108px;animation:dmhd .52s ease-in-out infinite alternate}
@keyframes dmhd{from{transform:rotate(-4deg)}to{transform:rotate(4deg)}}
.dm-tf{transform-origin:112px 36px;animation:dmtf .26s ease-in-out infinite alternate}
@keyframes dmtf{from{transform:rotate(-7deg)}to{transform:rotate(7deg)}}
.dm-mo{transform-origin:97px 97px;animation:dmmo .26s ease-in-out infinite alternate}
@keyframes dmmo{from{transform:scaleY(.55)}to{transform:scaleY(1)}}
.dm-ey{transform-origin:97px 82px;animation:dmey 2.1s infinite}
@keyframes dmey{0%,92%,100%{transform:scaleY(1)}96%{transform:scaleY(.1)}}
.dm-dr{transform-origin:110px 172px;animation:dmdr .26s ease-in-out infinite alternate}
@keyframes dmdr{from{transform:scale(1)}to{transform:scale(1.035)}}
.dm-ts{animation:dmts .52s ease-in-out infinite alternate}
.dm-ts:nth-of-type(2n){animation-direction:alternate-reverse}
@keyframes dmts{from{transform:rotate(-12deg)}to{transform:rotate(12deg)}}
</style></head><body>
<div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div><div class="blob b4"></div>
<h1>✨ GLASS LUDO ✨</h1>
<div id="board" class="glass"><div id="grid"></div></div>
<div id="ui" class="glass">
  <div id="scene" class="wait"><div id="cube"></div></div>
  <div id="st">…</div>
  <button id="skip" class="hide" title="Skip absent player">⏭</button><button id="snd">🔊</button>
</div>
<div id="stamp">✍️ Developed by Yoginder Singh Negi</div>
<div id="tools"><button id="lite"></button><button id="spd"></button></div><div id="tl"><button id="quit" class="hide">🚪 Quit</button><button id="fin" class="hide">🏁 Finish</button></div><div id="net" class="hide"></div>
<div id="toonL" class="toon"><div class="bub">Wo maara! 🥁</div><svg viewBox="0 0 120 120"><g class="dh">
  <path d="M28 120 Q28 76 60 76 Q92 76 92 120Z" fill="#ff8c1a"/>
  <ellipse cx="60" cy="98" rx="40" ry="14" fill="#8b4a1c"/>
  <ellipse cx="21" cy="98" rx="7" ry="14" fill="#f5deb3" stroke="#6b3410" stroke-width="2"/>
  <ellipse cx="99" cy="98" rx="7" ry="14" fill="#f5deb3" stroke="#6b3410" stroke-width="2"/>
  <path d="M26 87 L40 109 L54 87 L68 109 L82 87 L94 107" stroke="#ffd23f" stroke-width="2.5" fill="none"/>
  <circle cx="60" cy="52" r="20" fill="#f2b27a"/>
  <path d="M38 50 Q38 22 60 22 Q82 22 82 50 Q60 40 38 50Z" fill="#e63946"/>
  <path d="M42 36 Q60 26 78 36" stroke="#ffd23f" stroke-width="3" fill="none"/>
  <circle cx="60" cy="26" r="5" fill="#ffd23f"/>
  <circle cx="52" cy="54" r="2.6" fill="#222"/><circle cx="68" cy="54" r="2.6" fill="#222"/>
  <path d="M47 63 Q54 57 60 62 Q66 57 73 63 Q66 68 60 64 Q54 68 47 63Z" fill="#222"/>
  <ellipse cx="60" cy="71" rx="5" ry="3.5" fill="#7a1f1f"/>
  <g class="s1"><line x1="42" y1="84" x2="24" y2="68" stroke="#f2b27a" stroke-width="7" stroke-linecap="round"/><line x1="24" y1="68" x2="14" y2="50" stroke="#8b5a2b" stroke-width="3.5" stroke-linecap="round"/></g>
  <g class="s2"><line x1="78" y1="84" x2="96" y2="68" stroke="#f2b27a" stroke-width="7" stroke-linecap="round"/><line x1="96" y1="68" x2="106" y2="50" stroke="#8b5a2b" stroke-width="3.5" stroke-linecap="round"/></g>
</g></svg></div>
<div id="toonR" class="toon"><div class="bub">Griha Pravesh 🏠</div><svg viewBox="0 0 140 120"><g>
  <path d="M34 118 L50 62 L78 62 L94 118Z" fill="#ff4fa3"/>
  <path d="M50 62 Q64 52 80 62 L86 92 Q70 82 52 88Z" fill="#ffd23f" opacity="0.92"/>
  <path d="M40 112 L88 112" stroke="#fff" stroke-width="2" stroke-dasharray="4 3"/>
  <circle cx="64" cy="42" r="19" fill="#f6c28b"/>
  <path d="M44 40 Q44 18 64 18 Q84 18 84 40 Q76 27 64 27 Q52 27 44 40Z" fill="#2b1b17"/>
  <ellipse cx="42" cy="52" rx="5" ry="11" fill="#2b1b17"/><ellipse cx="86" cy="52" rx="5" ry="11" fill="#2b1b17"/>
  <circle cx="42" cy="42" r="4" fill="#ff4fa3"/><circle cx="86" cy="42" r="4" fill="#ff4fa3"/>
  <circle cx="64" cy="31" r="2.2" fill="#e63946"/>
  <ellipse cx="57" cy="44" rx="3" ry="3.6" fill="#222"/><ellipse cx="71" cy="44" rx="3" ry="3.6" fill="#222"/>
  <circle cx="58" cy="42.6" r="1.1" fill="#fff"/><circle cx="72" cy="42.6" r="1.1" fill="#fff"/>
  <circle cx="51" cy="51" r="3.5" fill="#ff8fa3" opacity="0.6"/><circle cx="77" cy="51" r="3.5" fill="#ff8fa3" opacity="0.6"/>
  <path d="M58 52 Q64 58 70 52" stroke="#a33" stroke-width="2" fill="none" stroke-linecap="round"/>
  <g class="ft"><rect x="70" y="94" width="9" height="20" rx="4" fill="#f6c28b" transform="rotate(-8 74 94)"/><ellipse cx="82" cy="116" rx="10" ry="4.5" fill="#f6c28b"/><path d="M72 111 Q81 106 91 111" stroke="#ffd23f" stroke-width="2" fill="none"/></g>
  <g class="lt"><path d="M100 104 Q96 86 108 80 L122 80 Q134 86 130 104 Q130 117 115 117 Q100 117 100 104Z" fill="#e0a526" stroke="#b07a0f" stroke-width="2"/><ellipse cx="115" cy="80" rx="9" ry="3.5" fill="#fff2b0"/><circle cx="115" cy="72" r="8" fill="#8b5a2b"/><path d="M107 74 Q100 64 108 61 M123 74 Q130 64 122 61" stroke="#2ea043" stroke-width="4" fill="none" stroke-linecap="round"/></g>
  <circle class="rc" cx="124" cy="112" r="2" fill="#fff" style="--dx:10px"/><circle class="rc" cx="130" cy="114" r="2" fill="#fff" style="--dx:16px;animation-delay:.7s"/><circle class="rc" cx="120" cy="114" r="2" fill="#fff" style="--dx:6px;animation-delay:.9s"/>
</g></svg></div>
<div id="toast"></div>
<div id="setup" class="ov"><div class="glass">
  <h2 style="margin:0 0 2px">🎲 New Game</h2>
  <div class="by">Developed by Yoginder Singh Negi</div>
  <div style="font-size:13px;opacity:.9">Choose start corners</div>
  <div id="presets"><button data-p="d1">2P ⤡ Red–Yellow</button><button data-p="d2">2P ⤢ Green–Blue</button><button data-p="p3">3 Players</button><button data-p="p4">4 Players</button></div>
  <div id="opts"></div>
  <div class="row"><span>🏁 Win by getting</span><select id="winN"><option value="1">1 goti home</option><option value="2">2 goti home</option><option value="3">3 goti home</option><option value="4" selected>all 4 goti home</option></select></div>
  <div style="font-size:12px;opacity:.8">Tip: with 2 players use opposite corners.</div>
  <button id="go">▶ Start Game</button>
  <div style="margin-top:12px"><button id="goOnline" style="background:linear-gradient(90deg,#2de08a88,#4dabff88);font-size:17px">🌐 Play Online with Friends</button></div>
</div></div>
<div id="resume" class="ov hide"><div class="glass" style="width:min(90vw,360px)">
  <h2 style="margin:0 0 6px">👋 Welcome back</h2>
  <div id="rsOn" class="hide"><div>🌐 Online game · Room <b id="rsRoom"></b></div>
    <div class="row"><button id="rsOnGo">▶ Resume</button><button id="rsOnX">✖ Close session</button></div></div>
  <div id="rsOff" class="hide"><div>🎲 Offline game · <span id="rsInfo"></span></div>
    <div class="row"><button id="rsOffGo">▶ Resume</button><button id="rsOffX">✖ Close session</button></div></div>
  <div id="rsErr" style="color:#ffb3c1;min-height:18px;margin:4px 0"></div>
  <button id="rsNew">🆕 Start a new game</button>
</div></div>
<div id="online" class="ov hide"><div class="glass" style="width:min(90vw,360px)">
  <h2 style="margin:0 0 4px">🌐 Play Online</h2>
  <div id="onJoin">
    <div id="srv" class="hide" style="font-size:12px;opacity:.9;margin:4px 0 8px;word-break:break-all"></div>
    <input id="pname" maxlength="14" placeholder="Your name" autocomplete="off">
    <div class="row"><button id="mkRoom" style="width:100%">➕ Create room (be the host)</button></div>
    <div style="opacity:.8;font-size:13px">— or join a friend's room —</div>
    <div class="row"><input id="rcode" maxlength="4" placeholder="CODE" autocomplete="off"><button id="joinRoom">Join</button></div>
  </div>
  <div id="onLobby" class="hide">
    <div style="opacity:.85;font-size:13px">Room code</div><div id="rc"></div>
    <div class="row"><button id="shareBtn">📤 Invite friends</button><button id="copyBtn">📋 Copy link</button></div>
    <div style="font-size:13px;opacity:.85;margin-top:6px">Pick your start corner</div>
    <div id="pick"></div>
    <div id="seats"></div>
    <div id="lobMsg" class="by"></div>
    <div id="winRow" class="row hide"><span>🏁 Win by getting</span><select id="winLobby"><option value="1">1 goti home</option><option value="2">2 goti home</option><option value="3">3 goti home</option><option value="4" selected>all 4 goti home</option></select></div>
    <button id="startOn" class="hide" style="font-size:18px;background:linear-gradient(90deg,#ff4d6d99,#4dabff99)">▶ Start game</button>
  </div>
  <div id="onErr" style="color:#ffb3c1;margin:6px 0;min-height:18px"></div>
  <button id="onBack">← Back</button>
</div></div>
<div id="win" class="ov hide"><div class="glass"><h1 id="wt" style="font-size:34px;-webkit-text-fill-color:#fff"></h1><div id="rank" style="margin:8px 0;min-width:220px"></div><div class="by">Developed by Yoginder Singh Negi</div><button id="again">Play again</button></div></div>

<script>
/* ---------- geometry (L=6 -> standard 15x15 board, 52-step track) ---------- */
const L=6,N=2*L+3,M=L+1,Q=2*L+1,R=4*Q,LAST=R-2,HB=1000,FIN_P=HB+L-1;
const COLORS=['red','green','yellow','blue'];
const HEX={red:'#ff4d6d',green:'#2de08a',yellow:'#ffd23f',blue:'#4dabff'};
const NAME={red:'Red',green:'Green',yellow:'Yellow',blue:'Blue'};
const START={red:0,green:Q,yellow:2*Q,blue:3*Q};
const SAFE=new Set();COLORS.forEach(c=>{SAFE.add(START[c]);SAFE.add(START[c]+Q-5)});
const PATH=[];
function line(x,y,dx,dy,n){for(let i=0;i<n;i++)PATH.push([x+dx*i,y+dy*i])}
line(1,L,1,0,L-1);line(L,L-1,0,-1,L);line(M,0,1,0,2);
line(L+2,1,0,1,L-1);line(L+3,L,1,0,L);line(N-1,M,0,1,2);
line(N-2,L+2,-1,0,L-1);line(L+2,L+3,0,1,L);line(M,N-1,-1,0,2);
line(L,N-2,0,-1,L-1);line(L-1,L+2,-1,0,L);line(0,M,0,-1,2);
const I=[...Array(L-1).keys()].map(i=>i+1);
const HOME={red:I.map(i=>[i,M]),green:I.map(i=>[M,i]),yellow:I.map(i=>[N-1-i,M]),blue:I.map(i=>[M,N-1-i])};
const YOFF={red:[0,0],green:[L+3,0],yellow:[L+3,L+3],blue:[0,L+3]};
const yc=L/2,yd=L*.2,SPOT=[[yc-yd,yc-yd],[yc+yd,yc-yd],[yc-yd,yc+yd],[yc+yd,yc+yd]];
const cc=M+.5,FIN={red:[cc-.75,cc],green:[cc,cc-.75],yellow:[cc+.75,cc],blue:[cc,cc+.75]};
let FAST=false,SP=.5,BACKLOG=0;try{const v=parseFloat(localStorage.getItem('ludoSP'));if(v>0)SP=v}catch(e){}
const $=s=>document.querySelector(s),sleep=ms=>new Promise(r=>setTimeout(r,FAST?0:ms*SP*(BACKLOG>2?.15:1)));

/* ---------- build board ---------- */
const grid=$('#grid');grid.style.gridTemplate=`repeat(${N},1fr)/repeat(${N},1fr)`;
function cell(x,y,cls,col,txt){const d=document.createElement('div');d.className=cls;d.style.gridColumn=x+1;d.style.gridRow=y+1;
  if(col){d.style.background=`linear-gradient(145deg,${col},${col}bb)`;d.style.boxShadow=`0 0 8px ${col}aa`}
  if(txt)d.textContent=txt;grid.appendChild(d);return d}
COLORS.forEach(c=>{const [ox,oy]=YOFF[c];
  const y=cell(0,0,'yard',HEX[c]);y.style.gridArea=`${oy+1}/${ox+1}/${oy+1+L}/${ox+1+L}`;y.style.margin=`calc(var(--bs)/${N}*.75)`;
  const yi=document.createElement('div');yi.className='yi';yi.style.gridArea=`${oy+2}/${ox+2}/${oy+L}/${ox+L}`;yi.style.margin=`calc(var(--bs)/${N}*.2)`;grid.appendChild(yi)});
PATH.forEach(([x,y],i)=>{const hc=COLORS.find(c=>START[c]===i);
  cell(x,y,'c'+(hc?' col':''),hc?HEX[hc]:null,hc?'➤':(SAFE.has(i)?'★':''))});
COLORS.forEach(c=>HOME[c].forEach(([x,y])=>cell(x,y,'c',HEX[c])));
const ct=cell(0,0,'c');ct.id='ctr';ct.style.gridArea=`${L+1}/${L+1}/${L+4}/${L+4}`;

/* ---------- dice ---------- */
const PIPS={1:[4],2:[2,6],3:[2,4,6],4:[0,2,6,8],5:[0,2,4,6,8],6:[0,2,3,5,6,8]};
const FACE={1:'',6:'rotateY(180deg)',2:'rotateY(90deg)',5:'rotateY(-90deg)',3:'rotateX(90deg)',4:'rotateX(-90deg)'};
const SHOW={1:[0,0],6:[0,180],2:[0,-90],5:[0,90],3:[-90,0],4:[90,0]};
const TILT='rotateX(-16deg) rotateY(18deg)';
const cube=$('#cube');
for(let v=1;v<=6;v++){const f=document.createElement('div');f.className='f';f.style.transform=`${FACE[v]} translateZ(44px)`;
  for(let k=0;k<9;k++){const s=document.createElement('span');s.style.display='flex';if(PIPS[v].includes(k))s.innerHTML='<i></i>';f.appendChild(s)}cube.appendChild(f)}
cube.style.transform=`${TILT} rotateX(-20deg) rotateY(-30deg)`;

/* ---------- sound (synthesised, LOUD witch cackles) ---------- */
let AC,OUT,muted=false,boost=1;
function A(){if(!AC){AC=new(window.AudioContext||window.webkitAudioContext)();OUT=AC.createGain();OUT.gain.value=2.4;
  const cp=AC.createDynamicsCompressor();cp.threshold.value=-8;cp.ratio.value=12;OUT.connect(cp);cp.connect(AC.destination)}
  if(AC.state==='suspended')AC.resume();return AC}
function tone(type,f1,f2,t0,d,vol,flt){if(muted||FAST)return;const a=A(),o=a.createOscillator(),g=a.createGain(),f=a.createBiquadFilter();
  o.type=type;o.frequency.setValueAtTime(f1,t0);o.frequency.exponentialRampToValueAtTime(f2,t0+d);
  f.type='bandpass';f.frequency.value=flt||1500;f.Q.value=2;const v=Math.min(vol*boost,1);
  g.gain.setValueAtTime(.0001,t0);g.gain.exponentialRampToValueAtTime(v,t0+d*.2);g.gain.exponentialRampToValueAtTime(.0001,t0+d);
  o.connect(f);f.connect(g);g.connect(OUT);o.start(t0);o.stop(t0+d+.03)}
function noise(t0,d,vol,fr){if(muted||FAST)return;const a=A(),n=Math.floor(a.sampleRate*d),b=a.createBuffer(1,n,a.sampleRate),x=b.getChannelData(0);
  for(let i=0;i<n;i++)x[i]=Math.random()*2-1;const s=a.createBufferSource(),f=a.createBiquadFilter(),g=a.createGain();
  s.buffer=b;f.type='bandpass';f.frequency.setValueAtTime(fr,t0);f.frequency.exponentialRampToValueAtTime(fr/6,t0+d);
  g.gain.setValueAtTime(Math.min(vol*boost,1),t0);g.gain.exponentialRampToValueAtTime(.001,t0+d);s.connect(f);f.connect(g);g.connect(OUT);s.start(t0)}
const now=()=>A().currentTime+.02;
function sfxTick(){const t=now();tone('triangle',700,350,t,.07,.12,1200)}
function sfxRoll(){const t=now();for(let i=0;i<9;i++)tone('square',300+Math.random()*500,200,t+i*.09,.05,.05,900)}
function sfxSix(){boost=2.6;const t=now();
  for(let i=0;i<10;i++){const b=700-i*16,s=t+i*.14;
    tone('sawtooth',b,b*1.55,s,.08,.3,1500);tone('sawtooth',b*1.55,b*.7,s+.07,.08,.28,1200);
    tone('square',b*.5,b*.8,s,.12,.12,900);tone('sawtooth',b*2,b*3,s,.07,.12,2600)}
  tone('sawtooth',500,1600,t+1.45,.7,.32,2200);tone('square',250,800,t+1.45,.7,.15,1200);tone('sine',90,55,t,1.9,.3,200);noise(t,.35,.3,4000);boost=1}
function sfxCut(){boost=2.8;const t=now();tone('sawtooth',2400,110,t,.55,.35,2600);noise(t,.55,.45,3200);tone('sine',120,40,t,.6,.5,200);
  for(let i=0;i<8;i++){const s=t+.45+i*.21,b=330-i*18;
    tone('sawtooth',b,b*.5,s,.18,.42,800);tone('square',b*.5,b*.25,s,.18,.22,500);tone('sawtooth',b*2.2,b*1.2,s,.1,.12,1800)}
  tone('sawtooth',900,2600,t+2.2,.7,.32,2200);boost=1}
function sfxSorry(){boost=2.2;const t=now();
  tone('sine',1300,350,t,.55,.35,1800);   // cartoon slide-whistle drop
  tone('triangle',520,300,t+.6,.22,.35,1200);tone('triangle',460,260,t+.85,.22,.35,1100);tone('triangle',400,160,t+1.1,.6,.38,1000);   // "wah wah waaah"
  boost=1;if(FAST||muted)return;
  const say='Ooops... Sorryyy!';
  if(window.AndroidTTS){try{if(AndroidTTS.speakEx)AndroidTTS.speakEx(say,1.7,.85);else AndroidTTS.speak(say)}catch(e){}}
  else if(window.speechSynthesis){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(say);u.rate=.85;u.pitch=1.8;u.volume=1;speechSynthesis.speak(u)}catch(e){}}}
function sfxWin(){const t=now();[523,659,784,1047,1319].forEach((f,i)=>tone('triangle',f,f*1.01,t+i*.14,.5,.3,2000))}
function sfxHome(){const t=now();[784,988,1319].forEach((f,i)=>tone('triangle',f,f*1.01,t+i*.1,.3,.3,2000))}
/* --- Punjabi dhol (kill) --- */
function dholHit(t,k){if(k==='d'){tone('sine',160,52,t,.3,.7,320);noise(t,.07,.4,1300)}else if(k==='t'){noise(t,.05,.38,4800);tone('triangle',950,520,t,.07,.22,2600)}}
function sfxDhol(){boost=2.4;const t=now(),P='dttdtdttddtdttdt';for(let i=0;i<P.length;i++)dholHit(t+i*.15,P[i]);boost=1}
function voiceMaara(){if(muted||FAST)return;const say='Wo maara!';
  if(window.AndroidTTS){try{if(AndroidTTS.speakEx)AndroidTTS.speakEx(say,1.15,1);else AndroidTTS.speak(say)}catch(e){}return}
  if(window.speechSynthesis){try{speechSynthesis.cancel();const hv=(speechSynthesis.getVoices()||[]).some(v=>/^(hi|pa)/i.test(v.lang));
    const u=new SpeechSynthesisUtterance(hv?'वो मारा!':say);u.lang=hv?'hi-IN':'en-IN';u.rate=1;u.pitch=1.15;u.volume=1;speechSynthesis.speak(u)}catch(e){}}}
function sfxKill(){sfxDhol();voiceMaara()}
/* --- wedding shehnai (home) --- */
function shNote(f,t,d,prev){const a=A(),o1=a.createOscillator(),o2=a.createOscillator(),lfo=a.createOscillator(),lg=a.createGain(),mix=a.createGain(),
    g1=a.createGain(),g2=a.createGain(),f1=a.createBiquadFilter(),f2=a.createBiquadFilter(),g=a.createGain();
  o1.type='sawtooth';o2.type='square';o2.detune.value=9;
  [o1,o2].forEach(o=>{o.frequency.setValueAtTime(prev,t);o.frequency.exponentialRampToValueAtTime(f,t+.08)});
  lfo.frequency.value=5.5;lg.gain.value=f*.014;lfo.connect(lg);lg.connect(o1.frequency);lg.connect(o2.frequency);
  g1.gain.value=.55;g2.gain.value=.22;o1.connect(g1);o2.connect(g2);g1.connect(mix);g2.connect(mix);
  f1.type='bandpass';f1.frequency.value=1250;f1.Q.value=3;f2.type='peaking';f2.frequency.value=2600;f2.gain.value=9;
  mix.connect(f1);f1.connect(f2);f2.connect(g);g.connect(OUT);
  g.gain.setValueAtTime(.0001,t);g.gain.linearRampToValueAtTime(.4,t+.07);g.gain.setValueAtTime(.36,t+d-.08);g.gain.linearRampToValueAtTime(.0001,t+d+.05);
  [o1,o2,lfo].forEach(o=>{o.start(t);o.stop(t+d+.08)})}
function sfxShehnai(){if(muted||FAST)return;const a=A(),t=now();
  const dr=a.createOscillator(),dg=a.createGain(),df=a.createBiquadFilter();dr.type='sawtooth';dr.frequency.value=130.8;df.type='lowpass';df.frequency.value=420;
  dg.gain.setValueAtTime(.0001,t);dg.gain.linearRampToValueAtTime(.12,t+.4);dg.gain.linearRampToValueAtTime(.0001,t+3.5);dr.connect(df);df.connect(dg);dg.connect(OUT);dr.start(t);dr.stop(t+3.6);
  const N=[[392,0,.32],[440,.32,.28],[494,.6,.28],[587,.88,.5],[523,1.4,.28],[494,1.68,.28],[440,1.96,.28],[494,2.24,.32],[392,2.6,.9]];
  N.forEach((n,i)=>shNote(n[0],t+n[1],n[2],i?N[i-1][0]:n[0]))}
/* --- cartoons --- */
function showToon(id,ms){if(FAST)return;const e=$('#'+id);e.classList.add('show');clearTimeout(e._t);e._t=setTimeout(()=>e.classList.remove('show'),ms)}
const HAMMER_SVG='<svg viewBox="0 0 100 100" width="100%" height="100%"><rect x="45" y="22" width="10" height="72" rx="4" fill="#b5651d" stroke="#6b3a10" stroke-width="2"/><rect x="18" y="6" width="64" height="30" rx="8" fill="#e63946" stroke="#7a1010" stroke-width="2"/><rect x="24" y="10" width="52" height="6" rx="3" fill="#fff" opacity="0.4"/><rect x="18" y="6" width="9" height="30" rx="4" fill="#ffd23f"/><rect x="73" y="6" width="9" height="30" rx="4" fill="#ffd23f"/><circle cx="42" cy="23" r="3.6" fill="#fff"/><circle cx="58" cy="23" r="3.6" fill="#fff"/><circle cx="43" cy="24" r="1.8" fill="#111"/><circle cx="59" cy="24" r="1.8" fill="#111"/><path d="M36 15 L47 19 M64 15 L53 19" stroke="#111" stroke-width="2.5" stroke-linecap="round"/></svg>';
/* ===== SLOW-MOTION HAMMER =====
   KILL_SLOW: 1 = old speed, bigger = slower.  2.0 = clear slow motion.  Change this one number to tune. */
const KILL_SLOW=2.0;
function sfxThud(){if(muted||FAST)return;const t=now();tone('sine',210,70,t,.16,.45,420);noise(t,.05,.25,900)}
/* the hammer (= the killer goti) hops square by square along its path, lands on the victim's square,
   hops beside it, winds up slowly and smashes it. trail = [[x,y],...] board-cell coordinates of the squares crossed. */
async function hammerHit(c,i,v,onHit,after,trail){
  if(FAST||!trail||trail.length<2){onHit&&onHit();after&&after();return}
  const bd=$('#board'),br=bd.getBoundingClientRect(),W=br.width,cs=W/N,kel=tokEl[c][i],vs=v.map(([o,j])=>tokEl[o][j]),K=ms=>ms*KILL_SLOW;
  const ctr=el=>{const r=el.getBoundingClientRect();return[r.left+r.width/2-br.left,r.top+r.height/2-br.top,r.width]};
  const [vx,vy,sz]=ctr(vs[0]),S=sz*2.8,R=.76*S;
  const dir=(br.left+vx+1.45*S<=innerWidth)?1:-1;            /* strike from the right side unless the screen edge is too near */
  const pts=trail.map(p=>[p[0]*cs,p[1]*cs]),strike=[vx+dir*R,vy];
  /* effects layer above the board, so the hammer is never clipped at the board edge */
  const fx=document.createElement('div');fx.style.cssText=`position:fixed;left:${br.left}px;top:${br.top}px;width:${W}px;height:${W}px;z-index:27;pointer-events:none;overflow:visible`;
  const w=document.createElement('div');w.style.cssText='position:absolute;left:0;top:0;width:0;height:0;will-change:transform';
  const h=document.createElement('div');h.style.cssText=`position:absolute;width:${S}px;height:${S}px;left:${-S/2}px;top:${-.94*S}px;transform-origin:50% 94%`;
  const sq=document.createElement('div');sq.style.cssText='width:100%;height:100%;transform-origin:50% 94%';sq.innerHTML=HAMMER_SVG;
  h.appendChild(sq);w.appendChild(h);fx.appendChild(w);document.body.appendChild(fx);
  const at=p=>`translate(${p[0]}px,${p[1]}px)`,rot=a=>`rotate(${a*dir}deg)`;
  w.style.transform=at(pts[0]);
  const ghosts=vs.map(el=>{const [x,y,gw]=ctr(el),gh=document.createElement('div');
    gh.style.cssText=`position:absolute;z-index:11;border-radius:50%;pointer-events:none;border:2px solid #fff;width:${gw}px;height:${gw}px;left:${x}px;top:${y}px;background:${el.style.background};box-shadow:0 3px 6px #0007;transform:translate(-50%,-50%)`;
    bd.appendChild(gh);el.style.visibility='hidden';return gh});
  kel.style.visibility='hidden';                              /* the killer goti turns into the hammer */
  /* 1) hammer pops out of the goti */
  sq.animate([{transform:'scale(.2)',opacity:0},{transform:'scale(1.15)',opacity:1,offset:.6},{transform:'scale(1)',opacity:1}],{duration:K(160),easing:'ease-out',fill:'forwards'});
  await rs(K(170));
  /* 2) hop square by square until it stands on the victim's square */
  const hop=async(a,b,dur,arc)=>{
    w.animate([{transform:at(a),easing:'ease-out'},{transform:`translate(${(a[0]+b[0])/2}px,${(a[1]+b[1])/2-arc}px)`,offset:.5,easing:'ease-in'},{transform:at(b)}],{duration:dur,fill:'forwards'});
    sq.animate([{transform:'scale(1,1)'},{transform:'scale(.9,1.12)',offset:.5},{transform:'scale(1,1)'}],{duration:dur});
    await rs(dur);w.style.transform=at(b);sfxTick();sfxThud();
    sq.animate([{transform:'scale(1.14,.84)'},{transform:'scale(1,1)'}],{duration:K(110)})};
  for(let k=1;k<pts.length;k++){await hop(pts[k-1],pts[k],K(200),cs*1.1)}
  /* 3) last little hop beside the victim, to take the striking position */
  await rs(K(90));
  await hop(pts[pts.length-1],strike,K(240),cs*.9);
  await rs(K(120));
  /* 4) slow wind-up, tense pause, slow smash */
  h.animate([{transform:rot(0)},{transform:rot(62),offset:.3,easing:'ease-in-out'},{transform:rot(62),offset:.5,easing:'ease-in'},{transform:rot(-90)}],{duration:K(1000),fill:'forwards'});
  await rs(K(1000));
  /* 5) impact, in slow motion */
  onHit&&onHit();sfxThud();
  const sh=dir*6;
  bd.animate([{transform:'translate(0,0)'},{transform:`translate(${-sh}px,4px)`},{transform:`translate(${sh}px,-4px)`},{transform:`translate(${-sh*.6}px,2px)`},{transform:'translate(0,0)'}],{duration:K(300)});
  burst(ghosts[0],26,['#fff','#ffd23f','#ff4d6d']);
  h.animate([{transform:rot(-90)},{transform:rot(-72),offset:.4},{transform:rot(-90)}],{duration:K(300),delay:K(40)});
  const gd=K(800);
  ghosts.forEach(gh=>gh.animate([{transform:'translate(-50%,-50%) scale(1,1)'},{transform:'translate(-50%,-30%) scale(1.6,.18)',offset:.25},
    {transform:'translate(-50%,-30%) scale(1.6,.18)',offset:.6},{transform:'translate(-50%,-260%) scale(.2) rotate(500deg)',opacity:0}],{duration:gd,fill:'forwards'}));
  w.animate([{opacity:1},{opacity:1,offset:.55},{opacity:0}],{duration:gd,fill:'forwards'});
  await rs(gd*.95);
  ghosts.forEach(gh=>gh.remove());after&&after();vs.forEach(el=>el.style.visibility='');kel.style.visibility='';
  await rs(K(60));fx.remove()}

/* ===== cartoon dhol boy: appears in the goti's yard whenever a goti comes out of it ===== */
const DHOL_CELLS=2.3,DHOL_MS=2800;       /* size in board squares (keep it small) / how long he plays */
const DHOL_SVG=`<svg viewBox="0 0 200 240" xmlns="http://www.w3.org/2000/svg">
<g stroke-linejoin="round" stroke-linecap="round">
<path d="M70 168 L62 214 Q80 222 98 214 L102 175Z" fill="#ffa81f" stroke="#c46a00" stroke-width="2"/>
<path d="M110 172 L112 214 Q130 222 146 214 L142 170Z" fill="#ffa81f" stroke="#c46a00" stroke-width="2"/>
<path d="M62 212 Q80 220 98 212 M112 212 Q130 220 146 212" stroke="#e8480c" stroke-width="4" fill="none"/>
<path d="M56 216 Q80 210 100 218 Q104 231 80 231 Q56 233 56 216Z" fill="#7a3414" stroke="#4a1e08" stroke-width="2"/>
<path d="M108 218 Q128 210 150 216 Q166 224 150 231 Q120 233 108 218Z" fill="#7a3414" stroke="#4a1e08" stroke-width="2"/>
<g class="dm-bd">
<path d="M64 112 Q96 100 128 112 L142 180 Q96 192 54 180Z" fill="#ffa81f" stroke="#c46a00" stroke-width="2"/>
<path d="M84 108 L98 134 L112 108" stroke="#e8480c" stroke-width="4" fill="none"/>
<path d="M54 180 Q96 192 142 180" stroke="#e8480c" stroke-width="4" fill="none"/>
<path d="M118 106 L132 112 L160 150 L148 157Z" fill="#9b4dca"/>
<path d="M126 114 L132 122 L123 120Z M138 128 L145 134 L136 135Z" fill="#2ea64a" stroke="none"/>
<path d="M68 108 L82 108 L80 178 L66 178Z" fill="#9b4dca"/>
<path d="M69 120 L79 124 L69 130Z M68 140 L78 144 L68 150Z M67 160 L77 164 L67 170Z" fill="#2ea64a" stroke="none"/>
<g stroke="none"><circle cx="78" cy="112" r="3.6" fill="#ff4d6d"/><circle cx="82" cy="119" r="3.6" fill="#ffd23f"/><circle cx="88" cy="127" r="3.6" fill="#2de08a"/><circle cx="94" cy="131" r="3.6" fill="#4dabff"/><circle cx="98" cy="132" r="3.6" fill="#ff4d6d"/><circle cx="102" cy="131" r="3.6" fill="#ffd23f"/><circle cx="108" cy="127" r="3.6" fill="#2de08a"/><circle cx="114" cy="119" r="3.6" fill="#4dabff"/><circle cx="118" cy="112" r="3.6" fill="#ff4d6d"/></g>
<g transform="rotate(-9 110 172)"><g class="dm-dr">
<path d="M44 138 Q110 126 176 142 L176 206 Q110 218 44 206Z" fill="#a8441a" stroke="#5a1f0a" stroke-width="2.5"/>
<ellipse cx="176" cy="174" rx="12" ry="32" fill="#8a3410" stroke="#5a1f0a" stroke-width="2.5"/>
<path d="M84 134 Q91 172 84 210 M140 136 Q147 172 140 210" stroke="#6e1c08" stroke-width="5" fill="none"/>
<polyline points="52,140 88,205 120,138 152,206 174,148" stroke="#f3e2c4" stroke-width="3" fill="none"/>
<polyline points="52,206 88,138 120,207 152,136 174,198" stroke="#f3e2c4" stroke-width="3" fill="none"/>
<ellipse cx="44" cy="172" rx="17" ry="35" fill="#f6e8cf" stroke="#6b3410" stroke-width="3"/>
<ellipse cx="44" cy="174" rx="8" ry="14" fill="#d9c3a0" stroke="none"/>
<g class="dm-ts" style="transform-origin:90px 206px"><line x1="90" y1="206" x2="90" y2="216" stroke="#f3e2c4" stroke-width="2"/><path d="M85 217 Q90 212 95 217 L96 228 L84 228Z" fill="#e8300c" stroke="none"/></g>
<g class="dm-ts" style="transform-origin:124px 210px"><line x1="124" y1="210" x2="124" y2="219" stroke="#f3e2c4" stroke-width="2"/><path d="M119 220 Q124 215 129 220 L130 231 L118 231Z" fill="#ff8c1a" stroke="none"/></g>
<g class="dm-ts" style="transform-origin:160px 205px"><line x1="160" y1="205" x2="160" y2="214" stroke="#f3e2c4" stroke-width="2"/><path d="M155 215 Q160 210 165 215 L166 226 L154 226Z" fill="#e8300c" stroke="none"/></g>
</g></g>
<path d="M68 120 L44 128" stroke="#c46a00" stroke-width="17"/><path d="M68 120 L44 128" stroke="#ffa81f" stroke-width="14"/>
<path d="M124 120 L152 112" stroke="#c46a00" stroke-width="17"/><path d="M124 120 L152 112" stroke="#ffa81f" stroke-width="14"/>
<g class="dm-hd">
<circle cx="68" cy="82" r="7" fill="#e0985f" stroke="#a3592b" stroke-width="2"/><circle cx="127" cy="82" r="7" fill="#e0985f" stroke="#a3592b" stroke-width="2"/>
<circle cx="97" cy="80" r="29" fill="#e0985f" stroke="#a3592b" stroke-width="2"/>
<circle cx="81" cy="92" r="5" fill="#ff8f8f" opacity=".35" stroke="none"/><circle cx="113" cy="92" r="5" fill="#ff8f8f" opacity=".35" stroke="none"/>
<path d="M66 76 Q62 36 98 31 Q134 36 130 74 Q114 58 98 60 Q82 58 66 76Z" fill="#ff7a1a" stroke="#b94a00" stroke-width="2"/>
<path d="M68 64 Q98 40 128 60 L126 68 Q98 50 70 72Z" fill="#ffb21a" stroke="none"/>
<g class="dm-tf"><ellipse cx="112" cy="18" rx="6.5" ry="17" transform="rotate(-38 112 36)" fill="#ffb21a" stroke="#b94a00" stroke-width="1.5"/><ellipse cx="112" cy="18" rx="6.5" ry="17" transform="rotate(-19 112 36)" fill="#ff7a1a" stroke="#b94a00" stroke-width="1.5"/><ellipse cx="112" cy="18" rx="6.5" ry="17" fill="#ffb21a" stroke="#b94a00" stroke-width="1.5"/><ellipse cx="112" cy="18" rx="6.5" ry="17" transform="rotate(19 112 36)" fill="#ff7a1a" stroke="#b94a00" stroke-width="1.5"/><ellipse cx="112" cy="18" rx="6.5" ry="17" transform="rotate(38 112 36)" fill="#ffb21a" stroke="#b94a00" stroke-width="1.5"/></g>
<path d="M97 62 Q100 68 97 73 Q94 68 97 62Z" fill="#e8300c" stroke="none"/>
<path d="M79 75 Q86 70 92 75 M102 75 Q108 70 115 75" stroke="#2a1408" stroke-width="2.4" fill="none"/>
<g class="dm-ey" stroke="none"><ellipse cx="86" cy="83" rx="3.4" ry="4.4" fill="#2a1408"/><ellipse cx="108" cy="83" rx="3.4" ry="4.4" fill="#2a1408"/></g>
<path d="M99 86 Q103 91 97 93" stroke="#a3592b" stroke-width="2" fill="none"/>
<g class="dm-mo"><path d="M82 96 Q97 114 112 96Z" fill="#7a1f1f" stroke="none"/><path d="M85 97 Q97 103 109 97 L109 99 Q97 105 85 99Z" fill="#fff" stroke="none"/></g>
</g>
<g class="dm-l">
<path d="M44 128 L30 102" stroke="#c46a00" stroke-width="15"/><path d="M44 128 L30 102" stroke="#ffa81f" stroke-width="12"/>
<path d="M40 121 L33 108" stroke="#e8480c" stroke-width="13"/>
<path d="M29 98 Q8 80 18 42" stroke="#9c6b2c" stroke-width="6.5" fill="none"/><path d="M29 98 Q8 80 18 42" stroke="#f0c987" stroke-width="3.8" fill="none"/>
<circle cx="28" cy="97" r="8.5" fill="#e0985f" stroke="#a3592b" stroke-width="2"/>
</g>
<g class="dm-r">
<path d="M152 112 L162 86" stroke="#c46a00" stroke-width="15"/><path d="M152 112 L162 86" stroke="#ffa81f" stroke-width="12"/>
<path d="M155 104 L159 94" stroke="#e8480c" stroke-width="13"/>
<path d="M163 82 L187 34" stroke="#9c6b2c" stroke-width="6.5"/><path d="M163 82 L187 34" stroke="#f0c987" stroke-width="3.8"/>
<circle cx="163" cy="82" r="8.5" fill="#e0985f" stroke="#a3592b" stroke-width="2"/>
</g>
</g>
</g></svg>`;
function sfxDholOut(){if(muted||FAST)return;boost=2.2;const t=now(),P='dtdttdtdtd';for(let k=0;k<P.length;k++)dholHit(t+k*.15,P[k]);boost=1}
function showDholBoy(c){if(FAST)return;const bd=$('#board');let e=document.getElementById('dm_'+c);
  if(!e){e=document.createElement('div');e.id='dm_'+c;e.className='dm';e.innerHTML=DHOL_SVG;bd.appendChild(e)}
  const [ox,oy]=YOFF[c];e.style.width=(DHOL_CELLS/N*100)+'%';e.style.left=((ox+L/2)/N*100)+'%';e.style.top=((oy+L/2)/N*100)+'%';
  e.classList.remove('show');void e.offsetWidth;e.classList.add('show');sfxDholOut();
  clearTimeout(e._t);e._t=setTimeout(()=>e.classList.remove('show'),DHOL_MS)}
const clearDholBoys=()=>document.querySelectorAll('.dm').forEach(e=>e.remove());
$('#snd').onpointerdown=e=>{e.preventDefault();muted=!muted;$('#snd').textContent=muted?'🔇':'🔊'};

/* ---------- effects ---------- */
function toast(txt){const t=$('#toast');t.textContent=txt;t.classList.remove('show');void t.offsetWidth;t.classList.add('show')}
function flash(col){const d=document.createElement('div');Object.assign(d.style,{position:'fixed',inset:0,zIndex:25,pointerEvents:'none',background:`radial-gradient(circle,${col}99,transparent 70%)`});
  document.body.appendChild(d);d.animate([{opacity:0},{opacity:1},{opacity:0}],{duration:700}).onfinish=()=>d.remove()}
function burst(el,n=36,cols=Object.values(HEX)){const r=el.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;
  for(let i=0;i<n;i++){const p=document.createElement('div');
    Object.assign(p.style,{position:'fixed',left:cx+'px',top:cy+'px',width:'10px',height:'10px',borderRadius:'50%',background:cols[i%cols.length],zIndex:40,pointerEvents:'none',boxShadow:'0 0 10px '+cols[i%cols.length]});
    document.body.appendChild(p);const a=Math.random()*6.28,d=60+Math.random()*150;
    p.animate([{transform:'translate(0,0) scale(1)',opacity:1},{transform:`translate(${Math.cos(a)*d}px,${Math.sin(a)*d}px) scale(0)`,opacity:0}],{duration:900+Math.random()*500}).onfinish=()=>p.remove()}}

/* ---------- game state ---------- */
let mode={red:'human',green:'off',yellow:'cpu',blue:'off'},players=[],T={},killed={},cur=0,roll=0,phase='idle',busy=false,gen=0,sixCount=0,snap=null;
let leftSet=new Set(),ONLINE=false,me={},names={},lastN=0,sentRoll=false,sentMove=false,onlineOn=[],started=false,lobbySeats={},lobbyHost='',es=null,BASE='',pollGen=0,synced=false,WINN=4,ws=null,spinning=false,selfMoves=0;
function normBase(v){v=(v||'').trim();if(!v)return'';try{return new URL(/^https?:\/\//i.test(v)?v:((/^(\d+\.\d+\.\d+\.\d+|localhost)/.test(v)?'http://':'https://')+v)).origin}catch(e){return''}}
if(location.protocol==='file:'){try{BASE=normBase(localStorage.getItem('ludoServer'))}catch(e){}}
const tokEl={};
function buildSetup(){const o=$('#opts');o.innerHTML='';COLORS.forEach(c=>{const r=document.createElement('div');r.className='row';
  r.innerHTML=`<span><span class="dot" style="background:${HEX[c]};color:${HEX[c]}"></span>${NAME[c]}</span>
  <select id="m_${c}"><option value="human">Human</option><option value="cpu">Computer</option><option value="off">Off</option></select>`;o.appendChild(r);$('#m_'+c).value=mode[c]})}
buildSetup();
const OPP={red:'yellow',yellow:'red',green:'blue',blue:'green'};
const PRE={d1:{red:'human',yellow:'cpu',green:'off',blue:'off'},d2:{green:'human',blue:'cpu',red:'off',yellow:'off'},p3:{red:'human',green:'cpu',yellow:'cpu',blue:'off'},p4:{red:'human',green:'cpu',yellow:'cpu',blue:'cpu'}};
document.querySelectorAll('#presets button').forEach(b=>b.onclick=()=>{Object.assign(mode,PRE[b.dataset.p]);COLORS.forEach(c=>$('#m_'+c).value=mode[c])});
$('#go').onclick=()=>{COLORS.forEach(c=>mode[c]=$('#m_'+c).value);players=COLORS.filter(c=>mode[c]!=='off');
  if(players.length<2){alert('Select at least 2 players');return}
  if(players.length===2&&OPP[players[0]]!==players[1]&&confirm('With 2 players, opposite corners are fairer. Move the second player to the opposite corner?')){
    const a=players[0],b=players[1],md=mode[b];mode[b]='off';mode[OPP[a]]=md;players=COLORS.filter(c=>mode[c]!=='off')}
  WINN=+$('#winN').value||4;
  A();$('#setup').classList.add('hide');newGame()};
$('#again').onclick=()=>{$('#win').classList.add('hide');$('#setup').classList.remove('hide')};

function newGame(res){gen++;phase='idle';leftSet.clear();$('#quit').classList.remove('hide');$('#fin').classList.toggle('hide',ONLINE&&!me.host);Object.values(tokEl).flat().forEach(e=>e.remove());clearDholBoys();
  T={};killed={};
  players.forEach(c=>{T[c]=res?res.T[c]:[-1,-1,-1,-1];killed[c]=res?!!res.killed[c]:false;tokEl[c]=[0,1,2,3].map(i=>{const e=document.createElement('div');e.className='tk';
    e.style.width=e.style.height=(100/N*.92)+'%';
    e.style.background=`radial-gradient(circle at 35% 30%,#fff,${HEX[c]} 55%,${HEX[c]}aa)`;e.style.color=HEX[c];$('#board').appendChild(e);return e})});
  cur=res?res.cur:0;busy=false;sixCount=0;snap=null;place();startTurn()}

function coord(c,i,p){if(p<0){const [ox,oy]=YOFF[c];return [SPOT[i][0]+ox,SPOT[i][1]+oy]}
  if(p<HB){const q=PATH[(START[c]+p)%R];return [q[0]+.5,q[1]+.5]}
  if(p-HB<L-1){const q=HOME[c][p-HB];return [q[0]+.5,q[1]+.5]}
  return FIN[c]}
function place(slow){const g={};
  players.forEach(c=>T[c].forEach((p,i)=>{const [x,y]=coord(c,i,p),k=p<0?c+i:x+','+y;(g[k]=g[k]||[]).push([c,i,x,y])}));
  Object.values(g).forEach(a=>a.forEach(([c,i,x,y],j)=>{const e=tokEl[c][i];e.style.transition=slow?'left .7s ease,top .7s ease':'';
    e.style.left=x/N*100+'%';e.style.top=y/N*100+'%';
    const n=a.length,ang=j/n*6.28;e.style.setProperty('--ox',n>1?Math.round(Math.cos(ang)*34)+'%':'0%');e.style.setProperty('--oy',n>1?Math.round(Math.sin(ang)*34)+'%':'0%')}))}

const pn=c=>names[c]||NAME[c];
const lockTxt=c=>killed[c]?'⚔️ home open':'🔒 cut a goti to open home';
function say(t){const c=players[cur];$('#st').innerHTML=`<div><b style="background:${HEX[c]}">${pn(c)}</b> ${t}<br><small>${lockTxt(c)}</small></div>`}
function shade(h,f){const n=parseInt(h.slice(1),16);return '#'+[16,8,0].map(k=>Math.round(((n>>k)&255)*f).toString(16).padStart(2,'0')).join('')}
function startTurn(){if(phase==='over')return;
  if(leftSet.has(players[cur])){phase='skip';busy=true;const g=gen;setTimeout(()=>{if(g===gen&&phase==='skip'){busy=false;nextTurn()}},250*SP);return}
  phase='roll';busy=false;const c=players[cur];if(!ONLINE)saveLocal();
  $('#scene').style.setProperty('--pc',HEX[c]);$('#scene').style.setProperty('--pd',shade(HEX[c],.55));
  const mine=!ONLINE||c===me.color;
  say(mode[c]==='cpu'?'(CPU) rolling…':mine?'tap the dice 🎲':'is playing…');
  $('#scene').classList.remove('six','sad');$('#scene').classList.toggle('wait',mode[c]==='human'&&mine);updSkip();
  if(mode[c]==='cpu'){const g=gen;setTimeout(()=>{if(g===gen)rollDice()},550*SP)}}
$('#scene').onpointerdown=e=>{e.preventDefault();A();
  if(ONLINE){if(phase==='roll'&&players[cur]===me.color&&!sentRoll){sentRoll=true;startSpin();setTimeout(()=>{sentRoll=false;if(spinning)stopSpin()},6000);post({t:'roll'})}return}
  if(phase==='roll'&&mode[players[cur]]==='human')rollDice()};

/* tap anywhere near a glowing token to move it */
$('#board').addEventListener('pointerdown',e=>{if(phase!=='move')return;const c=players[cur];if(mode[c]!=='human'||(ONLINE&&c!==me.color))return;
  const r=$('#board').getBoundingClientRect();let best=null,bd=1e9;
  tokEl[c].forEach((el,i)=>{if(!el.classList.contains('can'))return;const b=el.getBoundingClientRect(),d=Math.hypot(e.clientX-(b.left+b.width/2),e.clientY-(b.top+b.height/2));if(d<bd){bd=d;best=i}});
  if(best!==null&&bd<r.width/N*2.2){e.preventDefault();ONLINE?sendMove(best):doMove(c,best)}});

/* move simulation: returns list of positions the token will pass, or null if illegal */
function stepsList(c,p,r){if(p<0)return r===6?[0]:null;const out=[];
  for(let s=0;s<r;s++){if(p>=HB){if(p>=FIN_P)return null;p++}else p=(p%R===LAST&&killed[c])?HB:p+1;out.push(p)}return out}
const movable=c=>[0,1,2,3].filter(i=>stepsList(c,T[c][i],roll)!==null);
function victims(c,np){if(np<0||np>=HB)return[];const a=(START[c]+np)%R;if(SAFE.has(a))return[];const v=[];
  players.forEach(o=>{if(o!==c)T[o].forEach((p,j)=>{if(p>=0&&p<HB&&(START[o]+p)%R===a)v.push([o,j])})});return v}
function choose(c,mv){let best=mv[0],bs=-1;mv.forEach(i=>{const p=T[c][i],l=stepsList(c,p,roll),np=l[l.length-1];let s=Math.random()*5;
  if(np===FIN_P)s+=100;if(victims(c,np).length)s+=80;if(p<0)s+=(killed[c]?40:50);if(np>=HB)s+=30;
  if(np<HB&&SAFE.has((START[c]+np)%R))s+=12;if(p>=0&&p<HB)s+=(p%R)/8;if(s>bs){bs=s;best=i}});return best}

function startSpin(){spinning=true;const sc=$('#scene');sc.classList.remove('wait','six','sad');sc.classList.add('rolling');sc.style.animationDuration='1.2s';
  cube.style.transition='transform 1.6s linear';cube.style.transform=`${TILT} rotateX(1440deg) rotateY(1800deg)`;sfxRoll()}
function stopSpin(){spinning=false;const sc=$('#scene');sc.classList.remove('rolling');sc.style.animationDuration='';cube.style.transition='none';cube.style.transform=`${TILT} rotateX(0deg) rotateY(0deg)`}
async function rollDice(forced){if(busy||phase!=='roll')return;busy=true;phase='rolling';const g=gen,sc=$('#scene'),c=players[cur];
  const was=spinning;spinning=false;A();sc.classList.remove('wait','six','sad');if(!was){sc.classList.add('rolling');sc.style.animationDuration=SP+'s';sfxRoll()}
  roll=forced||(1+Math.floor(Math.random()*6));
  if(roll===6){sixCount++;if(sixCount===1)snap=JSON.stringify({T,killed})}else sixCount=0;
  const [ax,ay]=SHOW[roll];cube.style.transition=`transform ${SP}s cubic-bezier(.2,.8,.2,1)`;
  cube.style.transform=`${TILT} rotateX(${ax+(was?1800:720)+Math.round(Math.random()*2)*360}deg) rotateY(${ay+(was?2160:1080)}deg)`;
  await sleep(1050);if(g!==gen)return;
  sc.classList.remove('rolling');sc.style.animationDuration='';cube.style.transition='none';cube.style.transform=`${TILT} rotateX(${ax}deg) rotateY(${ay}deg)`;
  const mv=(roll===6&&sixCount===3)?[]:movable(c),useless=roll===6&&sixCount<3&&!mv.length;
  if(roll===6){if(useless){sc.classList.add('sad');sfxSorry();toast('😅 Ooops… Sorryy!')}else{sc.classList.add('six');sfxSix();flash('#ffd23f');burst(sc,60)}}
  if(roll===6&&sixCount===3){toast('🚫 3 SIXES! Turn lost');say('rolled 3 sixes!');await sleep(1300);if(g!==gen)return;
    const s=JSON.parse(snap);players.forEach(p=>T[p]=s.T[p]);Object.assign(killed,s.killed);place(true);sixCount=0;await sleep(900);if(g!==gen)return;nextTurn();return}
  if(roll===6&&!useless)toast('🧙‍♀️ SIX! Hehehe!');
  if(!mv.length){say(`rolled ${roll} – no move`);await sleep(550);if(g!==gen)return;nextTurn();return}
  phase='move';busy=false;
  if(mode[c]==='cpu'){await sleep(350);if(g!==gen)return;doMove(c,choose(c,mv))}
  else{const mine=!ONLINE||c===me.color,auto=mv.length===1||mv.every(i=>T[c][i]===T[c][mv[0]]);
    say(mine?`rolled ${roll} – tap a goti`:`rolled ${roll}`);if(mine)mv.forEach(i=>tokEl[c][i].classList.add('can'));
    if(ONLINE){if(mine&&auto)setTimeout(()=>{if(g===gen&&phase==='move')sendMove(mv[0])},450*SP)}
    else if(auto){await sleep(450);if(g===gen&&phase==='move')doMove(c,mv[0])}}}

async function doMove(c,i){if(busy||phase!=='move')return;busy=true;phase='moving';const g=gen;
  tokEl[c].forEach(e=>e.classList.remove('can'));
  const list=stepsList(c,T[c][i],roll);let warned=false;
  const fromYard=T[c][i]<0,willKill=victims(c,list[list.length-1]).length>0,trail=[coord(c,i,T[c][i])];
  for(const np of list){const prev=T[c][i];
    if(prev>=0&&prev<HB&&prev%R===LAST&&!killed[c]&&!warned){warned=true;toast('🔒 Cut a goti first!')}
    T[c][i]=np;
    if(willKill){trail.push(coord(c,i,np));continue}        /* a killing move: the hammer itself hops over these squares */
    place();sfxTick();if(fromYard)showDholBoy(c);await sleep(150);if(g!==gen)return}
  const np=T[c][i];let extra=roll===6;
  const v=victims(c,np);
  if(v.length){
    await hammerHit(c,i,v,()=>{sfxKill();showToon('toonL',2900);flash('#ffb000');toast('🥁 Wo maara!')},()=>{v.forEach(([o,j])=>T[o][j]=-1);killed[c]=true;place()},trail);
    if(g!==gen)return;
    burst(tokEl[c][i],50,[HEX[c],'#fff','#ffd23f']);extra=true;await sleep(600);if(g!==gen)return}
  if(np===FIN_P){sfxShehnai();showToon('toonR',3500);toast('🏠 Griha Pravesh!');burst(tokEl[c][i],40);extra=true;await sleep(400)}
  if(T[c].filter(x=>x===FIN_P).length>=WINN){endGame(c);return}
  if(extra)startTurn();else nextTurn()}

function endGame(w0){phase='over';busy=true;gen++;clearLocal();try{localStorage.removeItem('ludoSess')}catch(e){}$('#fin').classList.add('hide');$('#quit').classList.add('hide');
  const prog=c=>T[c].reduce((a,x)=>a+(x<0?0:x<HB?x:LAST+1+(x-HB)),0);
  const rows=players.map(c=>({c,h:T[c].filter(x=>x===FIN_P).length,p:prog(c)})).sort((a,b)=>b.h-a.h||b.p-a.p);
  if(w0){const wi=rows.findIndex(r=>r.c===w0);if(wi>0)rows.unshift(rows.splice(wi,1)[0])}
  const w=rows[0].c;sfxWin();$('#wt').textContent='🏆 '+pn(w)+' wins!';$('#wt').style.color=HEX[w];
  const box=$('#rank');box.innerHTML='';
  rows.forEach((r,i)=>{const d=document.createElement('div');d.className='row';const l=document.createElement('span'),dot=document.createElement('span');
    dot.className='dot';dot.style.background=HEX[r.c];dot.style.color=HEX[r.c];l.append(dot,document.createTextNode((i+1)+'. '+pn(r.c)));
    const rr=document.createElement('span');rr.textContent=r.h+' home';d.append(l,rr);box.appendChild(d)});
  $('#win').classList.remove('hide');for(let k=0;k<5;k++)setTimeout(()=>burst($('#wt'),50),k*300)}
$('#quit').onclick=()=>{if(!confirm(ONLINE?'Quit this game? You leave your seat and the others carry on.':'Quit this game and go back to the menu?'))return;
  if(ONLINE){const x={room:me.room,id:me.id};leaveOnline();api('/api/leave',x)}else clearLocal();
  gen++;phase='idle';busy=true;['#fin','#quit','#skip','#win'].forEach(q=>$(q).classList.add('hide'));
  Object.values(tokEl).flat().forEach(e=>e.remove());clearDholBoys();$('#st').textContent='';
  $('#onJoin').classList.remove('hide');$('#onLobby').classList.add('hide');$('#setup').classList.remove('hide')};
$('#fin').onclick=()=>{if(phase==='over')return;if(!confirm('Finish the game now and show the result?'))return;if(ONLINE)post({t:'finish'});else endGame()};
function saveLocal(){try{localStorage.setItem('ludoGame',JSON.stringify({players,mode,T,killed,cur,WINN,t:Date.now()}))}catch(e){}}
function loadLocal(){try{return JSON.parse(localStorage.getItem('ludoGame')||'null')}catch(e){return null}}
function clearLocal(){try{localStorage.removeItem('ludoGame')}catch(e){}}
function nextTurn(){sixCount=0;snap=null;cur=(cur+1)%players.length;startTurn()}

/* ================= ONLINE MULTIPLAYER ================= */
const store=()=>{try{return JSON.parse(localStorage.getItem('ludoSess')||'null')}catch(e){return null}};
const MQ=[];let qrun=false;
async function api(path,body){try{const r=await fetch(BASE+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();
  if(j.error==='not found')j.error='Wrong server address - use only the main game link (nothing after .com)';return j}catch(e){return{error:'Cannot reach the game server - check internet / server address'}}}
function post(msg){if(ws&&ws.readyState===1){try{ws.send(JSON.stringify(msg));return Promise.resolve()}catch(e){}}return postHTTP(msg)}
async function postHTTP(msg,tries=3){for(let i=0;i<tries;i++){
    try{const r=await fetch(BASE+'/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room:me.room,id:me.id,msg})});if(r.ok)return}catch(e){}
    await rs(500*(i+1))}
  toast('⚠ Connection problem - resyncing');if(msg.t==='move'){try{sessionStorage.setItem('autoResume','1')}catch(e){}setTimeout(()=>location.reload(),1200)}}
function sendMove(i){if(sentMove||phase!=='move')return;sentMove=true;setTimeout(()=>sentMove=false,6000);selfMoves++;post({t:'move',i});doMove(me.color,i)}   // moves instantly on your screen
const onErr=t=>{$('#onErr').textContent=t||''};
const inviteUrl=()=>`${BASE||location.origin}/?room=${me.room}`;
function enter(res){if(res.error){onErr(res.error);return}
  ONLINE=true;me={id:res.id,color:res.color,room:res.room,host:false};lastN=0;started=false;names={};
  try{localStorage.setItem('ludoSess',JSON.stringify({room:me.room,id:me.id,name:$('#pname').value.trim()}))}catch(e){}
  $('#onJoin').classList.add('hide');$('#onLobby').classList.remove('hide');$('#rc').textContent=me.room;connect()}
function connect(){pollGen++;synced=false;FAST=true;openWS(pollGen);pingLoop(pollGen)}
function openWS(g){let opened=false,w;
  try{w=new WebSocket(`${(BASE||location.origin).replace(/^http/,'ws')}/ws?room=${me.room}&id=${me.id}&after=${lastN}`)}catch(e){ws=null;pollLoop(g);return}
  ws=w;
  const fb=setTimeout(()=>{if(!opened&&g===pollGen){try{w.close()}catch(e){}ws=null;pollLoop(g)}},4500);   // WebSocket blocked -> use long-poll instead
  w.onopen=()=>{opened=true;clearTimeout(fb);onErr('')};
  w.onmessage=e=>{const d=JSON.parse(e.data);if(d.n){if(d.n<=lastN)return;lastN=d.n}handle(d)};
  w.onclose=()=>{clearTimeout(fb);if(g!==pollGen||!ONLINE||ws!==w)return;ws=null;if(opened){onErr('Reconnecting…');setTimeout(()=>{if(g===pollGen&&ONLINE)openWS(g)},600)}}}
const rs=ms=>new Promise(r=>setTimeout(r,ms));
async function pingLoop(g){
  while(g===pollGen&&ONLINE){const t=performance.now(),e=$('#net');
    try{await fetch(BASE+'/health',{cache:'no-store'});const ms=Math.round(performance.now()-t);e.classList.remove('hide');e.textContent=(ms<150?'🟢 ':ms<400?'🟡 ':'🔴 ')+ms+' ms'}
    catch(x){e.classList.remove('hide');e.textContent='🔴 offline'}
    await rs(6000)}
  $('#net').classList.add('hide')}
async function pollLoop(g){let fails=0;
  while(g===pollGen&&ONLINE){
    try{const ctl=new AbortController(),to=setTimeout(()=>ctl.abort(),32000);
      const r=await fetch(`${BASE}/api/poll?room=${me.room}&id=${me.id}&after=${lastN}`,{signal:ctl.signal,cache:'no-store'});clearTimeout(to);
      const j=await r.json();if(g!==pollGen)return;
      if(j.error){onErr('Room closed (server restarted). Go back and create a new room.');return}
      fails=0;onErr('');
      if(j.on){onlineOn=j.on;renderSeats();updSkip()}
      for(const d of j.msgs){if(d.n<=lastN)continue;lastN=d.n;handle(d)}
      if(!j.more&&!synced){synced=true;if(!qrun&&!MQ.length)FAST=false}
    }catch(e){if(g!==pollGen)return;fails++;onErr('Reconnecting…');await rs(Math.min(700*fails,3000))}}}
function handle(d){
  if(d.t==='lobby'){names={};Object.entries(d.seats).forEach(([c,n])=>names[c]=n);me.host=d.host===me.color;lobbySeats=d.seats;lobbyHost=d.host;renderLobby();if(started&&phase!=='over')$('#fin').classList.toggle('hide',!me.host)}
  else if(d.t==='presence'){onlineOn=d.on;renderSeats();updSkip()}
  else if(d.t==='synced'){synced=true;if(!qrun&&!MQ.length)FAST=false}
  else if(d.t==='closed'){leaveOnline();onErr('The host closed this room.');$('#win').classList.add('hide');$('#online').classList.remove('hide');$('#onJoin').classList.remove('hide');$('#onLobby').classList.add('hide')}
  else if(d.t==='start'){selfMoves=0;WINN=d.win||4;players=d.players;mode={red:'off',green:'off',yellow:'off',blue:'off'};players.forEach(c=>mode[c]='human');started=true;
    MQ.length=0;$('#online').classList.add('hide');$('#setup').classList.add('hide');$('#win').classList.add('hide');newGame()}
  else if(d.t==='roll'||d.t==='move'||d.t==='skip'||d.t==='finish'||d.t==='left'){MQ.push(d);if(!qrun)runQ()}}
function renderPick(){const b=$('#pick');b.innerHTML='';['red','green','blue','yellow'].forEach(c=>{const x=document.createElement('button');
  const taken=!!lobbySeats[c]&&c!==me.color;x.style.cssText=`background:${HEX[c]};border:3px solid ${c===me.color?'#fff':'transparent'};border-radius:14px;opacity:${taken?.25:1}`;
  x.textContent=c===me.color?'YOU':(taken?'•':'');x.disabled=taken;x.onclick=()=>pickSeat(c);b.appendChild(x)})}
async function pickSeat(c){if(c===me.color)return;const j=await api('/api/send',{room:me.room,id:me.id,msg:{t:'seat',color:c}});
  if(j.color){me.color=j.color;me.host=(lobbyHost===me.color);renderLobby()}else if(j.error)onErr(j.error)}
function renderLobby(){renderSeats();renderPick();$('#winRow').classList.toggle('hide',!me.host);const n=Object.keys(lobbySeats).length;
  $('#startOn').classList.toggle('hide',!(me.host&&n>=2));
  const cs=Object.keys(lobbySeats),adj=cs.length===2&&OPP[cs[0]]!==cs[1];
  $('#lobMsg').textContent=(n<2?'Waiting for friends to join… (send them the invite)':me.host?'Ready! Press Start when everyone has joined.':'Waiting for the host to start…')+(adj?' Tip: pick opposite corners for a fair 2-player game.':'')}
function renderSeats(){const box=$('#seats');box.innerHTML='';COLORS.forEach(c=>{if(!lobbySeats[c])return;
  const r=document.createElement('div');r.className='row';const l=document.createElement('span');
  const dot=document.createElement('span');dot.className='dot';dot.style.background=HEX[c];dot.style.color=HEX[c];
  const nm=document.createElement('span');nm.textContent=lobbySeats[c]+(c===me.color?' (you)':'')+(c===lobbyHost?' 👑':'');
  const on=document.createElement('span');on.textContent=onlineOn.includes(c)?'🟢':'⚪';
  l.append(dot,nm);r.append(l,on);box.appendChild(r)})}
async function until(f,ms=12000){const t=Date.now();while(!f()){if(Date.now()-t>ms)return false;await sleep(30)}return true}
async function runQ(){qrun=true;
  while(MQ.length){BACKLOG=MQ.length;const m=MQ.shift();
    if(m.t==='roll'){if(!await until(()=>phase==='roll'&&!busy))continue;if(m.c!==players[cur])continue;sentRoll=false;await rollDice(m.v)}
    else if(m.t==='move'){if(m.c===me.color&&selfMoves>0){selfMoves--;sentMove=false;continue}
      if(!await until(()=>phase==='move'))continue;const c=players[cur];if(m.c!==c)continue;sentMove=false;
      if(!(m.i>=0&&m.i<4)||stepsList(c,T[c][m.i],roll)===null)continue;await doMove(c,m.i)}
    else if(m.t==='skip'){if(await until(()=>phase==='roll'&&!busy))nextTurn()}
    else if(m.t==='left'){leftSet.add(m.c);const alive=players.filter(c=>!leftSet.has(c));
      if(alive.length<=1){await until(()=>phase==='roll'||phase==='move'||phase==='over'||phase==='skip',8000);if(phase!=='over')endGame(alive[0])}
      else if(players[cur]===m.c){await until(()=>phase==='roll'||phase==='move'||phase==='over',8000);
        if(players[cur]===m.c&&(phase==='roll'||phase==='move')){tokEl[m.c].forEach(e=>e.classList.remove('can'));nextTurn()}}}
    else if(m.t==='finish'){await until(()=>phase==='roll'||phase==='move'||phase==='over',8000);if(phase!=='over')endGame()}}
  qrun=false;BACKLOG=0;if(synced)FAST=false}
function updSkip(){const c=players[cur];
  $('#skip').classList.toggle('hide',!(ONLINE&&started&&me.host&&c&&onlineOn.length&&!onlineOn.includes(c)&&phase==='roll'))}
$('#skip').onpointerdown=e=>{e.preventDefault();post({t:'skip'})};
const SPEEDS=[[1,'🐢 Normal'],[.5,'⚡ Fast'],[.28,'🚀 Turbo']];
function setSP(v){SP=v;document.documentElement.style.setProperty('--tt',(.14*SP)+'s');try{localStorage.setItem('ludoSP',String(v))}catch(e){}
  const m=SPEEDS.find(x=>x[0]===v)||SPEEDS[1];$('#spd').textContent=m[1]}
$('#spd').onpointerdown=e=>{e.preventDefault();const i=SPEEDS.findIndex(x=>x[0]===SP);setSP(SPEEDS[(i+1)%SPEEDS.length][0])};
setSP(SPEEDS.some(x=>x[0]===SP)?SP:.5);
let LITE=null;try{LITE=localStorage.getItem('ludoLite')}catch(e){}
function setLite(on,save){document.body.classList.toggle('lite',on);$('#lite').textContent=on?'🪶 Lite':'✨ Full';if(save){try{localStorage.setItem('ludoLite',on?'1':'0')}catch(e){}}}
$('#lite').onpointerdown=e=>{e.preventDefault();setLite(!document.body.classList.contains('lite'),true)};
if(LITE==='1')setLite(true);else if(LITE==='0')setLite(false);
else{setLite((navigator.hardwareConcurrency||8)<=4);   // slow phones: switch effects off automatically
  let fr=0;const t0=performance.now();(function f(){fr++;const dt=performance.now()-t0;if(dt<1500)requestAnimationFrame(f);else if(fr/(dt/1000)<40)setLite(true)})()}
function leaveOnline(){pollGen++;if(ws){try{ws.close()}catch(e){}}ws=null;selfMoves=0;if(es)es.close();es=null;ONLINE=false;FAST=false;names={};started=false;onlineOn=[];lobbySeats={};try{localStorage.removeItem('ludoSess')}catch(e){}}
$('#again').addEventListener('click',()=>{leaveOnline();$('#onJoin').classList.remove('hide');$('#onLobby').classList.add('hide')});
function askServer(){const v=prompt('Enter your game server address, e.g. https://your-name.onrender.com');if(!v)return false;
  const b=normBase(v);if(!b){alert('That address does not look right');return false}BASE=b;try{localStorage.setItem('ludoServer',BASE)}catch(e){}return true}
function showSrv(){const e=$('#srv');if(location.protocol!=='file:'||!BASE){e.classList.add('hide');return}
  e.classList.remove('hide');e.innerHTML='';const t=document.createElement('span');t.textContent='Server: '+BASE+' ';
  const b=document.createElement('button');b.textContent='change';b.style.padding='3px 10px';b.onclick=()=>{if(askServer())showSrv()};e.append(t,b)}
$('#goOnline').onclick=()=>{A();if(location.protocol==='file:'&&!BASE&&!askServer())return;showSrv();
  $('#setup').classList.add('hide');$('#online').classList.remove('hide')};
$('#onBack').onclick=()=>{leaveOnline();$('#online').classList.add('hide');$('#setup').classList.remove('hide');$('#onJoin').classList.remove('hide');$('#onLobby').classList.add('hide');onErr('')};
$('#mkRoom').onclick=async()=>{const n=$('#pname').value.trim();if(!n){onErr('Enter your name first');return}onErr('');enter(await api('/api/create',{name:n}))};
$('#joinRoom').onclick=async()=>{const n=$('#pname').value.trim(),r=$('#rcode').value.trim().toUpperCase();
  if(!n||r.length<4){onErr('Enter your name and the 4-letter room code');return}onErr('');
  const s=store();enter(await api('/api/join',{name:n,room:r,id:(s&&s.room===r)?s.id:''}))};
$('#startOn').onclick=()=>post({t:'start',win:+$('#winLobby').value||4});
$('#shareBtn').onclick=async()=>{const url=inviteUrl(),txt=`Join my Ludo game! Room code: ${me.room}`;
  if(window.AndroidTTS&&AndroidTTS.share){AndroidTTS.share(txt+' '+url);return}
  if(navigator.share){try{await navigator.share({title:'Glass Ludo',text:txt,url});return}catch(e){}}
  window.open('https://wa.me/?text='+encodeURIComponent(txt+' '+url),'_blank')};
$('#copyBtn').onclick=async()=>{try{await navigator.clipboard.writeText(inviteUrl());$('#lobMsg').textContent='Link copied ✔'}catch(e){prompt('Copy this invite link',inviteUrl())}};
function refreshResume(){const s=store(),g=loadLocal();$('#rsOn').classList.toggle('hide',!s);$('#rsOff').classList.toggle('hide',!g);
  if(s)$('#rsRoom').textContent=s.room;if(g)$('#rsInfo').textContent=g.players.map(c=>NAME[c]).join(', ');
  if(!s&&!g){$('#resume').classList.add('hide');$('#setup').classList.remove('hide')}}
function showResume(){if(!store()&&!loadLocal())return false;$('#setup').classList.add('hide');$('#resume').classList.remove('hide');refreshResume();return true}
async function resumeOnline(){const s=store();if(!s)return;$('#rsErr').textContent='Connecting…';
  const res=await api('/api/join',{name:s.name||'Player',room:s.room,id:s.id});
  if(res.error){$('#rsErr').textContent='That online game is no longer available.';try{localStorage.removeItem('ludoSess')}catch(e){}refreshResume();return}
  $('#rsErr').textContent='';$('#resume').classList.add('hide');$('#online').classList.remove('hide');$('#pname').value=s.name||'';enter(res)}
function resumeOffline(){const g=loadLocal();if(!g)return;players=g.players;mode=g.mode;WINN=g.WINN||4;$('#resume').classList.add('hide');$('#setup').classList.add('hide');A();newGame(g)}
$('#rsOnGo').onclick=resumeOnline;
$('#rsOnX').onclick=async()=>{const s=store();if(s)await api('/api/leave',{room:s.room,id:s.id});try{localStorage.removeItem('ludoSess')}catch(e){}$('#rsErr').textContent='';refreshResume()};
$('#rsOffGo').onclick=resumeOffline;
$('#rsOffX').onclick=()=>{clearLocal();refreshResume()};
$('#rsNew').onclick=()=>{$('#resume').classList.add('hide');$('#setup').classList.remove('hide')};
(function(){const q=(new URLSearchParams(location.search).get('room')||'').toUpperCase();
  if(!q){if(sessionStorage.getItem('autoResume')==='1'){sessionStorage.removeItem('autoResume');if(store()){showResume();resumeOnline();return}}showResume();return}
  const s=store();
  $('#setup').classList.add('hide');$('#online').classList.remove('hide');$('#rcode').value=q;$('#pname').value=(s&&s.name)||'';
  if(s&&s.room===q&&s.id&&s.name)api('/api/join',{name:s.name,room:q,id:s.id}).then(enter)})();
if('serviceWorker' in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('/sw.js').catch(()=>{});
</script></body></html>
"""


ICON192 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAADlElEQVR42u3dPXITQRRFYWlKGyCmKLMBHJHDBvBOCL0EIjLYBhErIIdIRIQExCzBBEpE2WD9jKbf7f5OaE1Zre4z9/VUy8/ruzdvV/g31x+fmYT/MJkCEAgEAoFAIIBAIBAIBAIBBAKBQCAQCCAQCAQCgUAAgUAgEAgEAoEAAoFAIBAIBBAIBAKBQCCAQCAQCAQCAQQCgUAgpLNJGuznD8u/57bRZ73++T5iTdbV2/y2kKYalWUqLBB1EjQqKRB1cjSa2JPF9uqWQOzpx6EyJYw6meVsYo8o6msPhCgKCCR+kkNoYg+HYgViT75D9kAIFUj8dBFCEgiJAomfXkJIAoFAaMcm/QM8ffLy/g9//f5mtMvQ4jB1pg3Qg4tRdmEWG+3CJ6ypJezR9TjwGqMdroQdNdG7ixtGUdZobaJBoAvkfKvqkDXa/gU6Z2aXX5Ws0SphINCFb8olb+us0UogEAgEAoEAAoFAINDMnH9CtOQZU9ZoJRAIdOGbcvkbOmu0oyTQaTPbaj2yRquEoQF5Xyjb3aAHHhU1v5uzRjtQAh0y13XWI2u0nSfQITd3wcXIGu0QAiXOfrQrNtEgEAgEAgEEgqewy9Hf8zaBWqqz/xKNlLBT7DnqGglEnccvFkUSCARaPH7UMgLN5gGHCAQCNYofIUQgEAhN2azebc1CTzz/uug/PJBAIBAIBAJFMk4XBAKBQN2FkAN5Ap3uAXsIhHPxhbK/4qTjLggSqEotY48EOjGKqEMgG2QlDAQCgQACgUDwFHYWWc/beiRWX4z9l0otTK89G6b+7DnqGqMdLoGyuiB037PBJhojCZTVBWGEng1T9/a0WpVBejYoYRhDoKwuCOP0bJBAIBAIBAKBQACBQKAHyOqCME7PBgmEYQTK6oIwSM+GsATK6oIwQs8GJQxnkfeFsqwuCN33bEhNoKwuCB33bFjfbV81eNsXX+b6Tf4qY5+bT0pY11vO/no22ESDQBhOoO+vTf3sLL8BkkDIFUgI5cePBEK0QEIoPH4KJBCHku2pUcI4FGuPPRD6EEgIZcbPqtBZ2M6h+Q5ZqTNkCRNFUfaU3ANxKMeeVdGvcyhnCeoUFohGCeqUF+h+RRtJpsrSRAnUent080MEZm2iQSAQCCAQCAQCgUAAgUAgEAgEAggEAoFAIBAIBBAIBAKBQCCAQCAQCAQCAQQCgUAgEAggEAgEAoFAAIFAIBAIBMKI/AEzQkJZyJ8zLQAAAABJRU5ErkJggg==")
ICON512 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAIAAAB7GkOtAAAJyklEQVR42u3dMXLTXBiGUZvRBlx7GNhAXLknG3B24jJLSJUOtkHFCtLjylSUKVx7CaaAIo2RksjWvfc9p4ZMfn2/vkdXJpP5abOdQarVt48uArE+uAQAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACACAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACACAAAAgAAAIAAACAIAAACAAAAgAAPXpXIIG/fjqGgy0dwleY/X86CK0ZH7abF0F6x4kQQCw9EEMBAB7H5RAALD6QQYEAHsflEAAsPpBBgQAqx9kQACw+kEG6uAngW1/uLb9p3sXwQkAqx9HAZwAbH9wFEAAbH/QAK7AKyCrH4rgdZATgO0PjgIIgO0PGoAA2P6gAQiA7Q8agADY/qABCIDtDxqAANj+oAEIgO0PGoAA2P6gAQiA7Q8agAAACAAe/8EhQACw/UEDBADbHzRAAAAQADz+g0OAAGD7gwYIAAAC4PEfcAgQAAAEwOM/4BAgAAAIgMd/wCFAAAAQAAAEoHDe/8CkvAUSAAAEwOM/OAQgAAAIAAACMBbvf6AY3gIJAAACAECfziXgr+Vi/f8/cDjuXCXTpCXz02brKrxaKx8A9K4J68M0K7J6fvS/gRMAF1wWL/+6DJgmAkDKpjj31ewO06RGPgS2L4r+ypgmTgCUfkt7jWCaOAGQuC88PJomApChqn8CdP172NYwzan4eWABYPq7VwNMEwEgcV/YGqaJADALv2NtDdNEAMi9V20N00QAyL1LbQ3TRADIvT9tDdNEAAAQAMIezTw2miYCQO49aWuYJgIAgAAAIAAknMe9NzBNBAAAASDsQcxjo2kiAAAIAAACAIAAMEiNL2G9ODZNBAAAAQBAAAAQAAAEAAABAEAAABAAAAQAAAEAQAAadTjufM+m6XtGAAAQAAAEAAABaFNdL2G9MjZNBAAAASDmQcwDo2kiAAAIAAACQNvncW8MTBMBIPGetC9MEwEAQACIeTTzwGiaCACJ96d9YZoIAIl3qX1hmggAifeqfWGaCACJd6x9YZoIAIlbw74wTQSAxK1hX5gmAkDi1rAvTJOKdC5BztZYLtaWhWmaJk4AHh7tC9M0TScAIrfGKM+PNoVpIgDEvUawLEwTAaCd1wi968OaME0EgPbXB6ZJAh8CAwgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAwEX5fQBk8ZtSQACw9Pv/sBggABCx+s/9dRlAACBl75/7akpAY3wIjO0//VcGJwAofUF7KYQTACRuf0cBBACit78GIACQu/01AAGA3O2vAQgA5G5/DUAAIH3zagACALk7VwMQAMjdthqAAAAgABD2oO0QgABA7obVAAQAAAEAQADgPWp5u+ItEAIAgABA2GO1QwACAIAAACAAAAgADFLjK3UfAyAAAAgAAAIAgAAAMI1u9rB3FYA2fP557yI4AQAgAAAIAAACACAAAAgAlOlw3PmeQQAAEAAABAAAAaBNdb1S9wEAAgCAAEDMY7XHfwQAAAEAQADgPcp/u+L9DwIAiRvW9kcAABAAiHnQ9viPAEDitrX9EQBI3Lm2PwIAiZvX9kcAIHH/2v4IACQ2wPZHACCxAbY/AgCJDbD9aUPnEtBYA5aLtdUPTgA4Ctj+4ARAZANGOQ3Y+wgA1FqCN2fA6kcAoJEDwZAYWPoIALQfAwjnQ2AAAQBAAAAQAAAEAAABAEAAABAAAAQAAAEAQAAAEAAABAAAAQBAAAC4KL8PgH/8phTTRACwJvr/sPVhmggAEcvi3F+3OEwTASBlU5z7anaHaVIjHwLbF0V/ZUwTJwBKv6W9RjBNnABI3BceHk0TASB6X9gapokAkLsvbA3TRADI3Re2hmkiAMzC71hbwzQRAHLvVVvDNBEAcu9SW8M0EQBy709bwzQRAAAEgLBHM4+NpokAkHtP2hqmiQAAIAAACAAJ53HvDUwTAQBAAAh7EPPYaJoIAAACAIAAACAADFLjS1gvjk0TAQBAAAAQAAAEAAABAEAAABAAAAQAAAEAQAAAEIBGHY4737Np+p4RAAAEAAABAEAA2lTXS1ivjE0TAQBAAIh5EPPAaJoIAAACAIAA0PZ53BsD00QASLwn7QvTRAAAEABiHs08MJomAkDi/WlfmCYCQOJdal+YJgJA4r1qX5gmAkDiHWtfmCYCQOLWsC9MEwFo1K9bW8O+MM0C3X33/4gAMN09bPubJhXpXIKcrbFcrC0L0zRNnAA8PNoXpmmaTgBEbo1Rnh9tCtNEAIh7jWBZmCYNmJ/2X1yFt7h5auw/qHd9WBOmWTL/BMgJAG8AME2G8iEwgAAAIAD0q+rngaFtPgAQAAAEAAABuCBvgaAA3v8IAAAC4BAAHv8RAAAEAAABGJe3QDAR738EAAABcAgAj/8IAAAC4BAAHv8RAAAEwCEAPP4LABoAtr8AACAAOASAx38BQAPA9hcANABsfwEAQABwCACP/wKABoDtLwBoANj+AqABgO0vABoA2P4CoAGA7S8AGgDY/gKgAWD7IwAaALY/AqABYPszss4lmLIBN0+uBFj9TgCOAmD7IwAaALY/l+cVUDEN8DoIqx8nAEcBsP1xAnAUAKsfAZABsPoRABkAqx8ByMiAEmDvIwAOBK4EVj8C4EAA9j4CkFwCMcDSRwDEQBKw7hEASbh1DYZutN9iSS4/CQwgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgAgAC4BgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAgAAAIAAACAAAAgCAAAAgAADU7Q906UiikR0yXgAAAABJRU5ErkJggg==")
MANIFEST = json.dumps({"name": "Glass Ludo", "short_name": "Glass Ludo", "start_url": "/", "scope": "/",
    "display": "standalone", "orientation": "portrait", "background_color": "#1b0b3a", "theme_color": "#1b0b3a",
    "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
              {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]})
SW = ("self.addEventListener('install',e=>self.skipWaiting());"
      "self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));"
      "self.addEventListener('fetch',e=>{const u=new URL(e.request.url);"
      "if(e.request.method!=='GET'||u.pathname.startsWith('/api/')||u.origin!==location.origin)return;"
      "e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open('gl').then(k=>k.put(e.request,c));return r})"
      ".catch(()=>caches.match(e.request)))});")

COLORS = ["red", "green", "yellow", "blue"]
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOMS = {}
ROOMS_LOCK = threading.Lock()
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
ROOMS_FILE = os.environ.get("ROOMS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ludo_rooms.json"))
_save_pending = False


def schedule_save():
    """Save rooms to disk shortly after a change, so games survive a server restart (where the disk is kept)."""
    global _save_pending
    if _save_pending:
        return
    _save_pending = True
    threading.Timer(1.5, do_save).start()


def do_save():
    global _save_pending
    _save_pending = False
    try:
        with ROOMS_LOCK:
            items = list(ROOMS.items())
        data = {}
        for code, r in items:
            with r.lock:
                data[code] = {"seats": dict(r.seats), "names": dict(r.names), "host": r.host,
                              "started": r.started, "log": list(r.log), "touch": r.touch, "left": list(r.left)}
        tmp = ROOMS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, ROOMS_FILE)
    except Exception:
        pass


def load_rooms():
    try:
        with open(ROOMS_FILE) as f:
            data = json.load(f)
    except Exception:
        return
    now = time.time()
    for code, d in data.items():
        if now - d.get("touch", 0) > 6 * 3600:
            continue
        r = Room(code)
        r.seats, r.names, r.host = d["seats"], d["names"], d["host"]
        r.started, r.log, r.touch = d["started"], d["log"], now
        r.left = set(d.get("left", []))
        ROOMS[code] = r
RNG = random.SystemRandom()


class Room:
    """One online game. Server picks dice values and relays every action to all players in order."""
    def __init__(self, code):
        self.code = code
        self.seats = {}      # colour -> client id
        self.names = {}      # client id -> display name
        self.host = None     # client id of host
        self.started = False
        self.log = []        # ordered game messages (lets players reconnect / catch up)
        self.conns = {}      # client id -> [Queue,...] (open event streams)
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.left = set()    # colours of players who quit mid-game
        self.seen = {}       # client id -> last time it polled
        self.touch = time.time()

    def color_of(self, cid):
        for c, i in self.seats.items():
            if i == cid:
                return c
        return None

    def append(self, msg):
        with self.lock:
            msg["n"] = len(self.log) + 1
            self.log.append(msg)
            self.cond.notify_all()
            schedule_save()
            for qs in self.conns.values():
                for q in qs:
                    q.put((msg["n"], msg))
            self.touch = time.time()

    def transient(self, msg):
        with self.lock:
            for qs in self.conns.values():
                for q in qs:
                    q.put((None, msg))

    def online_colors(self):
        now = time.time()
        return [c for c, i in self.seats.items() if i in self.conns or now - self.seen.get(i, 0) < 35]

    def lobby(self):
        return {"t": "lobby", "seats": {c: self.names[i] for c, i in self.seats.items()},
                "host": self.color_of(self.host)}

    def presence(self):
        with self.lock:
            on = self.online_colors()
        self.transient({"t": "presence", "on": on})


def clean_name(n):
    n = " ".join(str(n or "").split())[:14]
    return n or "Player"


def new_id():
    return os.urandom(8).hex()


OPP = {"red": "yellow", "yellow": "red", "green": "blue", "blue": "green"}


def pick_free(r):
    """Prefer the corner opposite an existing player (2 players = diagonal), else first free corner."""
    for c in list(r.seats):
        if OPP[c] not in r.seats:
            return OPP[c]
    for c in COLORS:
        if c not in r.seats:
            return c


def api_create(d):
    with ROOMS_LOCK:
        for k in [k for k, r in ROOMS.items() if time.time() - r.touch > 6 * 3600]:
            del ROOMS[k]
        if len(ROOMS) > 500:
            return {"error": "Server is busy, try later"}
        while True:
            code = "".join(RNG.choice(CODE_CHARS) for _ in range(4))
            if code not in ROOMS:
                break
        r = Room(code)
        ROOMS[code] = r
    cid = new_id()
    with r.lock:
        r.seats["red"] = cid
        r.names[cid] = clean_name(d.get("name"))
        r.host = cid
        r.seen[cid] = time.time()
        r.append(r.lobby())
    return {"id": cid, "color": "red", "room": code}


def api_join(d):
    code = str(d.get("room", "")).strip().upper()
    r = ROOMS.get(code)
    if not r:
        return {"error": "Room not found - check the code"}
    cid = str(d.get("id") or "")
    with r.lock:
        if cid and cid in r.names:                       # re-join after refresh / reconnect
            if r.color_of(cid) in r.left:
                return {"error": "You left this game"}
            return {"id": cid, "color": r.color_of(cid), "room": code}
        if r.started:
            return {"error": "That game has already started"}
        free = [c for c in COLORS if c not in r.seats]
        if not free:
            return {"error": "Room is full (4 players)"}
        cid = new_id()
        col = pick_free(r)
        r.seats[col] = cid
        r.names[cid] = clean_name(d.get("name"))
        r.append(r.lobby())
    return {"id": cid, "color": col, "room": code}


def api_leave(d):
    """Close this device's session. Before the game starts the seat is freed (host leaving closes the room)."""
    code = str(d.get("room", "")).strip().upper()
    r = ROOMS.get(code)
    cid = str(d.get("id") or "")
    if not r or cid not in r.names:
        return {"ok": True}
    with r.lock:
        if not r.started:
            if cid == r.host:
                r.append({"t": "closed"})
                with ROOMS_LOCK:
                    ROOMS.pop(code, None)
                schedule_save()
            else:
                col = r.color_of(cid)
                if col:
                    del r.seats[col]
                del r.names[cid]
                r.append(r.lobby())
        else:                                   # game running: everyone is told this player left
            col = r.color_of(cid)
            if col and col not in r.left:
                r.left.add(col)
                if cid == r.host:               # hand "host" to someone still playing
                    for c, i in r.seats.items():
                        if c not in r.left:
                            r.host = i
                            break
                    r.append(r.lobby())
                r.append({"t": "left", "c": col})
    return {"ok": True}


def api_send(d):
    r = ROOMS.get(str(d.get("room", "")).upper())
    cid = str(d.get("id", ""))
    msg = d.get("msg") or {}
    if not r or r.color_of(cid) is None:
        return {"error": "not in room"}
    color, t = r.color_of(cid), msg.get("t")
    with r.lock:
        if t == "start":
            if cid == r.host and not r.started and len(r.seats) >= 2:
                r.started = True
                w = msg.get("win")
                w = w if isinstance(w, int) and 1 <= w <= 4 else 4
                r.append({"t": "start", "win": w, "players": [c for c in COLORS if c in r.seats]})
        elif t == "seat" and not r.started:
            c = msg.get("color")
            if c in COLORS and c != color:
                if c in r.seats:
                    return {"error": "That corner is taken"}
                del r.seats[color]
                r.seats[c] = cid
                r.append(r.lobby())
                return {"ok": True, "color": c}
            return {"ok": True, "color": color}
        elif r.started and t == "roll":
            r.append({"t": "roll", "c": color, "v": RNG.randint(1, 6)})
        elif r.started and t == "move":
            i = msg.get("i")
            if isinstance(i, int) and 0 <= i < 4:
                r.append({"t": "move", "c": color, "i": i})
        elif r.started and t == "skip" and cid == r.host:
            r.append({"t": "skip"})
        elif r.started and t == "finish" and cid == r.host:
            r.append({"t": "finish"})
    return {"ok": True}


class H(http.server.BaseHTTPRequestHandler):
    server_version = "GlassLudo"
    protocol_version = "HTTP/1.1"      # keep-alive: faster repeated requests
    timeout = 70

    def setup(self):
        super().setup()
        try:
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # send small packets immediately
        except OSError:
            pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        if p in ("/", "/index.html"):
            return self._send(200, HTML, "text/html; charset=utf-8")
        if p == "/manifest.json":
            return self._send(200, MANIFEST, "application/manifest+json")
        if p == "/sw.js":
            return self._send(200, SW, "application/javascript")
        if p == "/icon-192.png":
            return self._send(200, ICON192, "image/png")
        if p == "/icon-512.png":
            return self._send(200, ICON512, "image/png")
        if p == "/health":
            return self._send(200, "ok", "text/plain")
        if p == "/ws":
            return self.ws(parse_qs(u.query))
        if p == "/api/poll":
            return self.poll(parse_qs(u.query))
        if p == "/api/events":
            return self.events(parse_qs(u.query))
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
        except Exception:
            return self._send(400, '{"error":"bad request"}')
        fn = {"/api/create": api_create, "/api/join": api_join, "/api/send": api_send, "/api/leave": api_leave}.get(urlparse(self.path).path.rstrip("/"))
        if not fn:
            return self._send(404, '{"error":"not found"}')
        self._send(200, json.dumps(fn(data)))

    def ws_read(self):
        """Read one WebSocket message (text/control frame) from the client."""
        f = self.rfile

        def need(n):
            b = f.read(n)
            if b is None or len(b) < n:
                raise OSError("closed")
            return b
        data, op0 = b"", None
        while True:
            b1, b2 = need(2)
            fin, op, masked, n = b1 & 0x80, b1 & 0x0F, b2 & 0x80, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", need(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", need(8))[0]
            if n > 65536:
                raise ValueError("frame too big")
            mask = need(4) if masked else b""
            payload = need(n)
            if masked:
                payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
            if op >= 8:
                return op, payload
            if op0 is None:
                op0 = op
            data += payload
            if fin:
                return op0, data

    def ws(self, q):
        """WebSocket: one always-open connection, messages pushed instantly both ways."""
        r = ROOMS.get(q.get("room", [""])[0].upper())
        cid = q.get("id", [""])[0]
        key = self.headers.get("Sec-WebSocket-Key")
        if not r or cid not in r.names or not key:
            return self._send(404, '{"error":"unknown room"}')
        try:
            after = max(0, int(q.get("after", ["0"])[0]))
        except ValueError:
            after = 0
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.close_connection = True
        sock = self.connection
        sock.settimeout(75)
        slock, qu, alive = threading.Lock(), queue.Queue(), threading.Event()
        alive.set()

        def send(op, payload=b""):
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            n = len(payload)
            head = bytes([0x80 | op])
            if n < 126:
                head += bytes([n])
            elif n < 65536:
                head += bytes([126]) + struct.pack(">H", n)
            else:
                head += bytes([127]) + struct.pack(">Q", n)
            with slock:
                sock.sendall(head + payload)

        with r.lock:
            for m in r.log[after:]:
                qu.put((m["n"], m))
            qu.put((None, {"t": "synced"}))
            r.conns.setdefault(cid, []).append(qu)
            r.seen[cid] = time.time()
        r.presence()

        def writer():
            try:
                while alive.is_set():
                    try:
                        item = qu.get(timeout=20)
                    except queue.Empty:
                        send(9)                    # keep-alive ping
                        continue
                    if item is None:
                        break
                    send(1, json.dumps(item[1]))
            except OSError:
                pass
            finally:
                alive.clear()
        threading.Thread(target=writer, daemon=True).start()
        try:
            while alive.is_set():
                op, payload = self.ws_read()
                if op == 8:
                    break
                if op == 9:
                    send(10, payload)
                elif op == 1:
                    try:
                        msg = json.loads(payload.decode("utf-8"))
                    except Exception:
                        continue
                    if isinstance(msg, dict):
                        api_send({"room": r.code, "id": cid, "msg": msg})
        except (OSError, ValueError):
            pass
        finally:
            alive.clear()
            qu.put(None)
            with r.lock:
                if cid in r.conns and qu in r.conns[cid]:
                    r.conns[cid].remove(qu)
                    if not r.conns[cid]:
                        del r.conns[cid]
            r.presence()
            try:
                send(8)
            except OSError:
                pass

    def poll(self, q):
        """Long-poll: wait (up to 20s) until there is a new message, then answer immediately."""
        r = ROOMS.get(q.get("room", [""])[0].upper())
        cid = q.get("id", [""])[0]
        if not r or cid not in r.names:
            return self._send(200, '{"error":"unknown room"}')
        try:
            after = max(0, int(q.get("after", ["0"])[0]))
        except ValueError:
            after = 0
        deadline = time.time() + 20
        with r.cond:
            r.seen[cid] = time.time()
            while len(r.log) <= after:
                left = deadline - time.time()
                if left <= 0:
                    break
                r.cond.wait(min(left, 5))
                r.seen[cid] = time.time()
            msgs = r.log[after:after + 300]
            more = len(r.log) > after + 300
        self._send(200, json.dumps({"msgs": msgs, "more": more, "on": r.online_colors()}))

    def events(self, q):
        r = ROOMS.get(q.get("room", [""])[0].upper())
        cid = q.get("id", [""])[0]
        if not r or cid not in r.names:
            return self._send(404, '{"error":"unknown room"}')
        try:
            last = int(self.headers.get("Last-Event-ID") or 0)
        except ValueError:
            last = 0
        qu = queue.Queue()
        with r.lock:
            for m in r.log[last:]:
                qu.put((m["n"], m))
            qu.put((None, {"t": "synced"}))
            r.conns.setdefault(cid, []).append(qu)
        r.presence()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                try:
                    n, m = qu.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                out = ("id: %d\n" % n if n else "") + "data: " + json.dumps(m) + "\n\n"
                self.wfile.write(out.encode("utf-8"))
                self.wfile.flush()
        except OSError:
            pass
        finally:
            with r.lock:
                if cid in r.conns and qu in r.conns[cid]:
                    r.conns[cid].remove(qu)
                    if not r.conns[cid]:
                        del r.conns[cid]
            r.presence()

    def log_message(self, *a):
        pass


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        pass            # ignore dropped phone connections quietly


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "YOUR-PC-IP"
    finally:
        s.close()


def main():
    load_rooms()
    hosted = "PORT" in os.environ            # cloud hosts give a PORT
    port = int(os.environ.get("PORT", 8000))
    while True:
        try:
            srv = Server(("0.0.0.0", port), H)
            break
        except OSError:
            if hosted:
                raise
            port += 1
    print("=" * 56)
    print(" Glass Ludo - ONLINE edition  (Developed by Yoginder Singh Negi)")
    print(f" This computer      : http://localhost:{port}")
    print(f" Same Wi-Fi friends : http://{lan_ip()}:{port}")
    print(" Friends anywhere   : see README_ONLINE.txt (tunnel / free hosting)")
    print("=" * 56)
    if not hosted:
        threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")


if __name__ == "__main__":
    main()
