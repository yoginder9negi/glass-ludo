#!/usr/bin/env python3
"""
GLASS LUDO v3 - web based, pure Python (no installs needed).
Run:  python ludo.py
 - Computer: http://localhost:8000
 - Mobile  : open the "On your mobile" link printed in the terminal (same Wi-Fi)
ONLINE MODE: "Play Online" -> Create room -> share the invite link/code. Friends open the link, enter a name and join.
  Host presses Start. Works on same Wi-Fi, or over the internet via a tunnel / free hosting (see README_ONLINE.txt).
Rules
 * Roll 6 to bring a token out. 6 / cutting a goti / reaching home = extra turn.
 * 3 sixes in a row = turn lost, all tokens go back to where they were.
 * First to bring all tokens home is 1st; play continues for 2nd, 3rd ... until one player is left.
 * A token can NOT enter home until its player has cut at least one opponent
   token. Until then it skips the home lane and keeps circling the board.
 * Exact number needed to reach the final home.

File layout
 1. HTML        - the whole game client (HTML + CSS + JS, one string)
 2. Assets      - icons, sounds, manifest, service worker (cached by the browser: ETag / 304)
 3. Room        - one online game: seats, ordered message log, live connections
 4. API         - create / join / leave / send
 5. HTTP + WS   - request handler, WebSocket + long-poll transport
 6. main()
"""
import base64
import gzip
import hashlib
import http.server
import json
import os
import queue
import random
import signal
import socket
import struct
import sys
import threading
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

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
body:not(:has(#setup:not(.hide))){animation:none}
.blob{position:fixed;border-radius:50%;opacity:.55;z-index:0;animation:fl 12s ease-in-out infinite alternate;pointer-events:none;will-change:transform}
.b1{width:320px;height:320px;background:radial-gradient(circle,#ff4d6d 0,#ff4d6d00 70%);top:-80px;left:-80px}
.b2{width:300px;height:300px;background:radial-gradient(circle,#2de08a 0,#2de08a00 70%);bottom:-60px;right:-60px;animation-delay:-4s}
.b3{width:260px;height:260px;background:radial-gradient(circle,#ffd23f 0,#ffd23f00 70%);top:40%;right:-100px;animation-delay:-7s}
.b4{width:280px;height:280px;background:radial-gradient(circle,#4dabff 0,#4dabff00 70%);bottom:10%;left:-100px;animation-delay:-2s}
@keyframes fl{to{transform:translate(60px,-50px) scale(1.2)}}
h1{margin:0;z-index:1;font-size:clamp(16px,3.2vw,26px);letter-spacing:3px;background:linear-gradient(90deg,#ff4d6d,#ffd23f,#2de08a,#4dabff);-webkit-background-clip:text;background-clip:text;color:transparent}
.glass{background:rgba(255,255,255,.12);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border:1px solid rgba(255,255,255,.35);box-shadow:0 10px 40px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.5)}
#board{--bs:min(98vw,calc(100vh - 212px),760px);--bs:min(98vw,calc(100dvh - 212px),760px);position:relative;width:var(--bs);height:var(--bs);border-radius:20px;z-index:1;overflow:hidden;touch-action:manipulation;backdrop-filter:none;-webkit-backdrop-filter:none}
#grid{position:absolute;inset:0;display:grid}
.c{margin:.6px;border-radius:24%;background:linear-gradient(145deg,#fff,#e7ecff);border:1px solid #fff;box-shadow:0 1px 3px #0004,inset 0 -2px 4px #0000001a;display:flex;align-items:center;justify-content:center;font-size:calc(var(--bs)/24);color:#ff9d00;font-weight:700}
.c.col{color:#fff;text-shadow:0 1px 3px #0006}
.yard{margin:0;border-radius:16px;border:1px solid rgba(255,255,255,.6)}
body.ios .glass,body.ios .ov{backdrop-filter:none;-webkit-backdrop-filter:none}   /* iPhone Safari: blur layers wash out the board colours */
body.ios .glass{background:rgba(50,30,110,.55)}
/* player tag in each start box: first 3 letters, glossy gold lettering. Back layer = outline + stacked edge + soft shadow,
   front layer = gold gradient with a diagonal sheen and a thin bright rim */
.yn{position:absolute;left:50%;top:50%;width:100%;transform:translate(-50%,-50%) rotate(-45deg);display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:none;
 font-family:"Arial Rounded MT Bold","Arial Black",Impact,"Trebuchet MS",sans-serif;font-weight:900;font-style:italic;font-size:calc(var(--bs)*.056);line-height:1.05;letter-spacing:.1em}
.yn .a{position:relative;display:block;color:transparent;white-space:nowrap;padding-right:.1em}
.yn .a::before,.yn .a::after{content:attr(data-t);position:absolute;left:0;top:0;width:100%;text-align:center;letter-spacing:inherit}
.yn .a::before{color:#6b3600;-webkit-text-stroke:.13em #6b3600;text-shadow:0 .04em 0 #9a5600,0 .08em 0 #7d4400,0 .12em 0 #5e3000,0 .2em .08em rgba(0,0,0,.45)}
.yn .a::after{background:linear-gradient(112deg,transparent 30%,rgba(255,255,255,.75) 42%,transparent 54%),linear-gradient(180deg,#fffbd0 0%,#ffe36e 22%,#f7b500 48%,#ffe27a 60%,#e09200 82%,#b86a00 100%);
 -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent;-webkit-text-stroke:.012em #fff3b0}
.yn .b{margin-top:.34em;font-size:.5em;font-style:normal;letter-spacing:.22em;color:#fff3c4;text-shadow:0 1px 1px #5a3000,0 0 4px #5a3000}
.yi{position:relative;overflow:hidden;border-radius:16px;background:rgba(255,255,255,.35);box-shadow:inset 0 0 18px #fff9}
#ctr{margin:0;border-radius:8px;background:conic-gradient(from -45deg,#2de08a 0 90deg,#ffd23f 90deg 180deg,#4dabff 180deg 270deg,#ff4d6d 270deg 360deg);box-shadow:inset 0 0 25px #fff8;border:1px solid #fff9}
.tk{position:absolute;border-radius:50%;pointer-events:none;transform:translate(calc(-50% + var(--ox,0%)),calc(-50% + var(--oy,0%)));transition:left var(--tt,.07s) linear,top var(--tt,.07s) linear;z-index:5;border:2px solid #fff;box-shadow:0 4px 8px #0007,inset -3px -4px 8px #0006,inset 3px 3px 6px #fffa}
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

/* --- name boxes, leaderboard --- */
.ov .glass{max-height:96vh;overflow:auto}
#opts .row{gap:6px}
.nm{flex:1;min-width:70px;max-width:150px;padding:7px 8px;font-size:14px;border-radius:10px}
.sr{display:flex;align-items:center;gap:8px;padding:7px 10px;margin:5px 0;border-radius:14px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.25);text-align:left}
.sr .rk{font-size:20px;width:30px;text-align:center;flex:none}
.sr .nm2{flex:1;min-width:0}
.sr .nm2 b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sr small{display:block;opacity:.85;font-size:11px;line-height:1.35}
.sr .wn{font-size:17px;font-weight:800;flex:none;color:#ffd23f}
.sr .sx{padding:2px 7px;font-size:11px;flex:none;background:rgba(255,255,255,.12)}
#stList{max-height:54vh;overflow:auto;min-width:min(80vw,320px)}
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
<div id="toonL" class="toon"><div class="bub">Chal haat! 🥁</div><svg viewBox="0 0 120 120"><g class="dh">
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
  <div style="font-size:13px;opacity:.9">Choose corners, player type and a name for each human player (first 3 letters shown in their start box)</div>
  <div id="presets"><button data-p="d1">2P ⤡ Red–Yellow</button><button data-p="d2">2P ⤢ Green–Blue</button><button data-p="p3">3 Players</button><button data-p="p4">4 Players</button></div>
  <div id="opts"></div>
  <div class="row"><span>🏁 Win by getting</span><select id="winN"><option value="1">1 goti home</option><option value="2">2 goti home</option><option value="3">3 goti home</option><option value="4" selected>all 4 goti home</option></select></div>
  <div style="font-size:12px;opacity:.8">Tip: with 2 players use opposite corners.</div>
  <button id="go">▶ Start Game</button>
  <div style="margin-top:12px"><button id="goOnline" style="background:linear-gradient(90deg,#2de08a88,#4dabff88);font-size:17px">🌐 Play Online with Friends</button></div>
  <div id="srvStat" class="by" style="margin-top:10px"></div>
  <div style="margin-top:10px"><button id="goStats" style="background:linear-gradient(90deg,#ffd23f77,#ff4d6d77);font-size:16px">🏆 Leaderboard &amp; Stats</button></div>
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
<div id="win" class="ov hide"><div class="glass"><h1 id="wt" style="font-size:34px;-webkit-text-fill-color:#fff"></h1><div id="rank" style="margin:8px 0;min-width:220px"></div><div class="by">Developed by Yoginder Singh Negi</div><div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap"><button id="again">Play again</button><button id="wStats">🏆 Leaderboard</button></div></div></div>
<div id="stats" class="ov hide"><div class="glass" style="width:min(94vw,400px)">
  <h2 style="margin:0 0 2px">🏆 Leaderboard</h2>
  <div class="by">Ranked by wins · saved on this device</div>
  <div id="stList"></div>
  <div class="row" style="justify-content:center"><button id="stClose">← Back</button><button id="stReset">🗑 Reset all</button></div>
</div></div>

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
const grid=$('#grid'),yardNm={};grid.style.gridTemplate=`repeat(${N},1fr)/repeat(${N},1fr)`;
function cell(x,y,cls,col,txt){const d=document.createElement('div');d.className=cls;d.style.gridColumn=x+1;d.style.gridRow=y+1;
  if(col){d.style.background=`linear-gradient(145deg,${col},${col}bb)`;d.style.boxShadow=`0 0 8px ${col}aa`}
  if(txt)d.textContent=txt;grid.appendChild(d);return d}
COLORS.forEach(c=>{const [ox,oy]=YOFF[c];
  const y=cell(0,0,'yard',HEX[c]);y.style.gridArea=`${oy+1}/${ox+1}/${oy+1+L}/${ox+1+L}`;y.style.margin=`calc(var(--bs)/${N}*.75)`;
  const yi=document.createElement('div');yi.className='yi';yi.style.gridArea=`${oy+2}/${ox+2}/${oy+L}/${ox+L}`;yi.style.margin=`calc(var(--bs)/${N}*.2)`;{const yn=document.createElement('div'),a=document.createElement('span'),b=document.createElement('span');yn.className='yn';a.className='a';b.className='b';yn.append(a,b);yi.appendChild(yn);yardNm[c]={box:yn,a,b}}grid.appendChild(yi)});
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
function sfxSorry(){boost=2.2;const t=now();
  tone('sine',1300,350,t,.55,.35,1800);   // cartoon slide-whistle drop
  tone('triangle',520,300,t+.6,.22,.35,1200);tone('triangle',460,260,t+.85,.22,.35,1100);tone('triangle',400,160,t+1.1,.6,.38,1000);   // "wah wah waaah"
  boost=1;if(FAST||muted)return;
  const say='Ooops... Sorryyy!';
  if(window.AndroidTTS){try{if(AndroidTTS.speakEx)AndroidTTS.speakEx(say,1.7,.85);else AndroidTTS.speak(say)}catch(e){}}
  else if(window.speechSynthesis){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(say);u.rate=.85;u.pitch=1.8;u.volume=1;speechSynthesis.speak(u)}catch(e){}}}
function sfxWin(){const t=now();[523,659,784,1047,1319].forEach((f,i)=>tone('triangle',f,f*1.01,t+i*.14,.5,.3,2000))}
/* --- Punjabi dhol (kill) --- */
function dholHit(t,k){if(k==='d'){tone('sine',160,52,t,.3,.7,320);noise(t,.07,.4,1300)}else if(k==='t'){noise(t,.05,.38,4800);tone('triangle',950,520,t,.07,.22,2600)}}
/* ----- recorded sounds: downloaded once (then cached by the browser), decoded into WebAudio buffers.
         If a clip is not ready yet, the synthesised sound is used instead. Volume of each can be changed here. ----- */
const CLIPS={chal:{url:'/a/chal.mp3',vol:1},dout:{url:'/a/dhol.mp3',vol:.85},win:{url:'/a/win.mp3',vol:.9}},BUF={},PLAYING={};
let clipsReq=false,clipAt=0;
async function loadClips(){if(clipsReq)return;clipsReq=true;
  await Promise.all(Object.keys(CLIPS).map(async k=>{try{const ab=await(await fetch(BASE+CLIPS[k].url)).arrayBuffer();
    BUF[k]=await new Promise((ok,no)=>{const r=A().decodeAudioData(ab,ok,no);if(r&&r.then)r.then(ok,no)})}catch(e){clipsReq=false}}))}
document.addEventListener('pointerdown',()=>setTimeout(loadClips,300),{once:true,capture:true});   /* after the first tap: phones allow sound */
function playClip(k,fail){if(muted||FAST)return;if(!BUF[k]){fail&&fail();return}
  try{const ac=A(),s=ac.createBufferSource(),g=ac.createGain();try{PLAYING[k]&&PLAYING[k].stop()}catch(e){}
    g.gain.value=CLIPS[k].vol;s.buffer=BUF[k];s.connect(g);g.connect(ac.destination);s.start();PLAYING[k]=s;if(k==='win')clipAt=Date.now()}catch(e){fail&&fail()}}
function voiceMaara(){playClip('chal',ttsChal)}
function sfxDholOut(){playClip('dout',synthDholOut)}
function ttsChal(){const say='Chal haat!';   /* fallback only if the recording cannot play */
  if(window.AndroidTTS){try{if(AndroidTTS.speakEx)AndroidTTS.speakEx(say,.8,1);else AndroidTTS.speak(say)}catch(err){}return}
  if(window.speechSynthesis){try{speechSynthesis.cancel();const hv=(speechSynthesis.getVoices()||[]).some(v=>/^(hi|pa)/i.test(v.lang));
    const u=new SpeechSynthesisUtterance(hv?'चल हट!':say);u.lang=hv?'hi-IN':'en-IN';u.rate=.8;u.pitch=1;u.volume=1;speechSynthesis.speak(u)}catch(err){}}}
function sfxKill(){voiceMaara()}   /* kill = only the "Chal haat!" voice, no dhol */
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
const HAMMER_SIZE=1.9;   /* hammer size in goti-widths (was 2.8). Smaller number = smaller hammer */
function sfxThud(){if(muted||FAST)return;const t=now();tone('sine',210,70,t,.16,.45,420);noise(t,.05,.25,900)}
/* the hammer (= the killer goti) hops square by square along its path, lands on the victim's square,
   hops beside it, winds up slowly and smashes it. trail = [[x,y],...] board-cell coordinates of the squares crossed. */
async function hammerHit(c,i,v,onHit,after,trail){
  if(FAST||!trail||trail.length<2){onHit&&onHit();after&&after();return}
  const bd=$('#board'),br=bd.getBoundingClientRect(),W=br.width,cs=W/N,kel=tokEl[c][i],vs=v.map(([o,j])=>tokEl[o][j]),K=ms=>ms*KILL_SLOW;
  const ctr=el=>{const r=el.getBoundingClientRect();return[r.left+r.width/2-br.left,r.top+r.height/2-br.top,r.width]};
  const [vx,vy,sz]=ctr(vs[0]),S=sz*HAMMER_SIZE,R=.76*S;
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
function synthDholOut(){if(muted||FAST)return;boost=2.2;const t=now(),P='dtdttdtdtd';for(let k=0;k<P.length;k++)dholHit(t+k*.15,P[k]);boost=1}
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
function burst(el,n=36,cols=Object.values(HEX)){n=Math.min(n,28);const r=el.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;
  for(let i=0;i<n;i++){const p=document.createElement('div');
    Object.assign(p.style,{position:'fixed',left:cx+'px',top:cy+'px',width:'10px',height:'10px',borderRadius:'50%',background:cols[i%cols.length],zIndex:40,pointerEvents:'none'});
    document.body.appendChild(p);const a=Math.random()*6.28,d=60+Math.random()*150;
    p.animate([{transform:'translate(0,0) scale(1)',opacity:1},{transform:`translate(${Math.cos(a)*d}px,${Math.sin(a)*d}px) scale(0)`,opacity:0}],{duration:900+Math.random()*500}).onfinish=()=>p.remove()}}

/* ---------- game state ---------- */
let mode={red:'human',green:'off',yellow:'cpu',blue:'off'},players=[],T={},killed={},cur=0,roll=0,phase='idle',busy=false,gen=0,sixCount=0,snap=null;
let gameT0=0,statDone=false,gameNames={},finished=[];
let leftSet=new Set(),ONLINE=false,me={},names={},lastN=0,sentRoll=false,sentMove=false,onlineOn=[],started=false,lobbySeats={},lobbyHost='',es=null,BASE='',pollGen=0,synced=false,WINN=4,ws=null,spinning=false,selfMoves=0;
function normBase(v){v=(v||'').trim();if(!v)return'';try{return new URL(/^https?:\/\//i.test(v)?v:((/^(\d+\.\d+\.\d+\.\d+|localhost)/.test(v)?'http://':'https://')+v)).origin}catch(e){return''}}
if(location.protocol==='file:'){try{BASE=normBase(localStorage.getItem('ludoServer'))}catch(e){}}
const tokEl={};
/* ================= SAVED NAME + LEADERBOARD ================= */
const lsGet=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:v}catch(err){return d}},lsSet=(k,v)=>{try{localStorage.setItem(k,v)}catch(err){}};
const getProfile=()=>lsGet('ludoProfile','');                 /* the name the player typed once - kept until they change it */
function saveProfile(n){n=(n||'').trim();if(n)lsSet('ludoProfile',n)}
let offNames={};try{offNames=JSON.parse(lsGet('ludoOffNames','{}'))||{}}catch(err){}
$('#pname').value=getProfile()||offNames.red||'';
$('#pname').addEventListener('input',()=>saveProfile($('#pname').value));
const SKEY='ludoStats';
function loadStats(){try{const x=JSON.parse(lsGet(SKEY,'null'));if(x&&x.p)return x}catch(err){}return{p:{}}}
const saveStats=x=>lsSet(SKEY,JSON.stringify(x));
const humanName=c=>mode[c]==='human'?String(gameNames[c]||names[c]||'').trim():'';   /* computer players are not recorded */
function recStats(res){if(statDone)return;statDone=true;const st=loadStats(),secs=Math.max(1,Math.round((Date.now()-gameT0)/1000));
  Object.keys(res).forEach(c=>{const n=humanName(c);if(!n)return;const k=n.toLowerCase();
    const o=st.p[k]||(st.p[k]={n,played:0,won:0,lost:0,quit:0,secs:0,last:0});
    o.n=n;o.played++;o[res[c]]++;o.secs+=secs;o.last=Date.now()});saveStats(st)}
function recQuit(){if(phase==='over'||statDone)return;const r={};if(ONLINE){if(me.color)r[me.color]='quit'}else players.forEach(c=>r[c]='quit');recStats(r)}
const fmtT=x=>{x=Math.round(x);const h=Math.floor(x/3600),m=Math.floor(x%3600/60);return h?h+'h '+String(m).padStart(2,'0')+'m':(m?m+'m':x+'s')};
function showStats(){const st=loadStats(),arr=Object.keys(st.p).map(k=>Object.assign({k},st.p[k])),rate=o=>o.played?o.won/o.played:0;
  arr.sort((a,b)=>b.won-a.won||rate(b)-rate(a)||a.quit-b.quit||b.played-a.played||b.last-a.last);
  const box=$('#stList');box.innerHTML='';
  if(!arr.length){const d=document.createElement('div');d.style.cssText='opacity:.85;padding:16px 6px';d.textContent='No games recorded yet. Finish a game with a name entered and it will appear here.';box.appendChild(d)}
  arr.forEach((o,i)=>{const r=document.createElement('div');r.className='sr';
    const rk=document.createElement('span');rk.className='rk';rk.textContent=['🥇','🥈','🥉'][i]||String(i+1);
    const mid=document.createElement('div');mid.className='nm2';const nb=document.createElement('b');nb.textContent=o.n;
    const sm=document.createElement('small');sm.textContent='▶ '+o.played+' played · 💔 '+o.lost+' lost · 🚪 '+o.quit+' quit · '+Math.round(rate(o)*100)+'% wins · ⏱ '+fmtT(o.secs);
    mid.append(nb,sm);const wn=document.createElement('span');wn.className='wn';wn.textContent='🏆 '+o.won;
    const x=document.createElement('button');x.className='sx';x.textContent='✖';x.title='Remove';
    x.onclick=()=>{if(confirm('Remove '+o.n+' from the leaderboard?')){const t=loadStats();delete t.p[o.k];saveStats(t);showStats()}};
    r.append(rk,mid,wn,x);box.appendChild(r)});
  $('#stats').classList.remove('hide')}
$('#goStats').onclick=showStats;$('#wStats').onclick=showStats;$('#stClose').onclick=()=>$('#stats').classList.add('hide');
$('#stReset').onclick=()=>{if(confirm('Delete ALL leaderboard data on this device?')){lsSet(SKEY,'{"p":{}}');showStats()}};

function buildSetup(){const o=$('#opts');o.innerHTML='';COLORS.forEach(c=>{const r=document.createElement('div');r.className='row';
  r.innerHTML=`<span style="white-space:nowrap"><span class="dot" style="background:${HEX[c]};color:${HEX[c]}"></span>${NAME[c]}</span>
  <input class="nm" id="n_${c}" maxlength="14" placeholder="Player name" autocomplete="off">
  <select id="m_${c}"><option value="human">Human</option><option value="cpu">Computer</option><option value="off">Off</option></select>`;o.appendChild(r);$('#m_'+c).value=mode[c];
  $('#n_'+c).value=offNames[c]||(c==='red'?(lsGet('ludoProfile','')):'');$('#m_'+c).onchange=syncNm});syncNm()}
function syncNm(){COLORS.forEach(c=>$('#n_'+c).classList.toggle('hide',$('#m_'+c).value!=='human'))}
buildSetup();
const OPP={red:'yellow',yellow:'red',green:'blue',blue:'green'};
const PRE={d1:{red:'human',yellow:'cpu',green:'off',blue:'off'},d2:{green:'human',blue:'cpu',red:'off',yellow:'off'},p3:{red:'human',green:'cpu',yellow:'cpu',blue:'off'},p4:{red:'human',green:'cpu',yellow:'cpu',blue:'cpu'}};
document.querySelectorAll('#presets button').forEach(b=>b.onclick=()=>{Object.assign(mode,PRE[b.dataset.p]);COLORS.forEach(c=>$('#m_'+c).value=mode[c]);syncNm()});
$('#go').onclick=()=>{COLORS.forEach(c=>mode[c]=$('#m_'+c).value);
  const blank=COLORS.filter(c=>mode[c]==='human'&&!$('#n_'+c).value.trim());
  if(blank.length&&confirm('Enter a name for each human player?\n\nOK = enter names now\nCancel = start with colour names')){$('#n_'+blank[0]).focus();return}
  const nm={};COLORS.forEach(c=>{const n=$('#n_'+c).value.trim();offNames[c]=n;if(mode[c]==='human'&&n)nm[c]=n});lsSet('ludoOffNames',JSON.stringify(offNames));players=COLORS.filter(c=>mode[c]!=='off');
  if(players.length<2){alert('Select at least 2 players');return}
  if(players.length===2&&OPP[players[0]]!==players[1]&&confirm('With 2 players, opposite corners are fairer. Move the second player to the opposite corner?')){
    const a=players[0],b=players[1],md=mode[b];mode[b]='off';mode[OPP[a]]=md;if(nm[b]){nm[OPP[a]]=nm[b];delete nm[b]}players=COLORS.filter(c=>mode[c]!=='off')}
  WINN=+$('#winN').value||4;names=nm;
  A();$('#setup').classList.add('hide');newGame()};
$('#again').onclick=()=>{$('#win').classList.add('hide');$('#setup').classList.remove('hide')};

function newGame(res){gen++;gameT0=Date.now();statDone=false;gameNames=Object.assign({},names);phase='idle';leftSet.clear();$('#quit').classList.remove('hide');$('#fin').classList.toggle('hide',ONLINE&&!me.host);Object.values(tokEl).flat().forEach(e=>e.remove());clearDholBoys();
  T={};killed={};finished=res&&res.finished?res.finished.slice():[];
  players.forEach(c=>{T[c]=res?res.T[c]:[-1,-1,-1,-1];killed[c]=res?!!res.killed[c]:false;tokEl[c]=[0,1,2,3].map(i=>{const e=document.createElement('div');e.className='tk';
    e.style.width=e.style.height=(100/N*.92)+'%';
    e.style.background=`radial-gradient(circle at 35% 30%,#fff,${HEX[c]} 55%,${HEX[c]}aa)`;e.style.color=HEX[c];$('#board').appendChild(e);return e})});
  cur=res?res.cur:0;busy=false;sixCount=0;snap=null;yardNames();place();startTurn()}

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
const PLACE=['1st','2nd','3rd'];
/* ---- first finisher celebration: short song clip (played once) + silent fireworks ---- */
const CLIP_MS=9700;
function crackers(ms){const cv=document.createElement('canvas'),lite=document.body.classList.contains('lite');   /* canvas fireworks, no sound */
  const W=cv.width=innerWidth,H=cv.height=innerHeight,x=cv.getContext('2d'),COL=['#ff4d6d','#ffd23f','#2de08a','#4dabff','#ffffff','#ff9f43','#c77dff'];
  cv.style.cssText='position:fixed;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:60';document.body.appendChild(cv);
  const R=[],P=[],t0=performance.now();let last=t0,nextR=0;
  function launch(){const tx=W*(.12+.76*Math.random());R.push({x:tx,y:H,tx,ty:H*(.15+.3*Math.random()),sp:H*(.0011+.0004*Math.random()),c:COL[Math.random()*COL.length|0]})}
  function boom(r){const n=lite?14:26,c=r.c;for(let i=0;i<n;i++){const a=i/n*6.283+Math.random()*.3,v=.05+Math.random()*.11;P.push({x:r.x,y:r.y,vx:Math.cos(a)*v*Math.min(W,H),vy:Math.sin(a)*v*Math.min(W,H),life:1,c:Math.random()<.25?'#fff':c})}}
  function frame(now){const dt=Math.min(now-last,40);last=now;const el=now-t0;x.clearRect(0,0,W,H);
    if(el<ms&&el>=nextR){launch();nextR=el+(lite?520:340)}
    for(let i=R.length-1;i>=0;i--){const r=R[i];r.y-=r.sp*dt;x.fillStyle=r.c;x.fillRect(r.x-1.5,r.y,3,10);if(r.y<=r.ty){boom(r);R.splice(i,1)}}
    for(let i=P.length-1;i>=0;i--){const p=P[i];p.vy+=.00006*Math.min(W,H)*dt;p.x+=p.vx*dt/16;p.y+=p.vy*dt/16;p.life-=dt/1100;if(p.life<=0){P.splice(i,1);continue}
      x.globalAlpha=p.life;x.fillStyle=p.c;x.fillRect(p.x-1.5,p.y-1.5,3,3)}
    x.globalAlpha=1;
    if(el<ms+1300||R.length||P.length)requestAnimationFrame(frame);else cv.remove()}
  requestAnimationFrame(frame)}
function celebrate(){try{crackers(CLIP_MS-1200)}catch(e){}playClip('win')}
function yardNames(){COLORS.forEach(c=>{const e=yardNm[c];if(!e)return;const on=players.includes(c),k=finished.indexOf(c),n=on?[...pn(c)].slice(0,3).join('').toUpperCase():'';   /* player name (diagonal, embossed) in own start box + finishing place */
  e.a.textContent=n;e.a.setAttribute('data-t',n);e.b.textContent=on&&k>=0?PLACE[k]:'';e.box.style.opacity=on&&leftSet.has(c)?.5:1})}
const lockTxt=c=>killed[c]?'⚔️ home open':'🔒 cut a goti to open home';
function say(t){const c=players[cur];$('#st').innerHTML=`<div><b style="background:${HEX[c]}">${pn(c)}</b> ${t}<br><small>${lockTxt(c)}</small></div>`}
function shade(h,f){const n=parseInt(h.slice(1),16);return '#'+[16,8,0].map(k=>Math.round(((n>>k)&255)*f).toString(16).padStart(2,'0')).join('')}
function startTurn(){if(phase==='over')return;
  if(isOut(players[cur])){phase='skip';busy=true;const g=gen;setTimeout(()=>{if(g===gen&&phase==='skip'){busy=false;nextTurn()}},250*SP);return}
  phase='roll';busy=false;const c=players[cur];if(!ONLINE)saveLocal();
  $('#scene').style.setProperty('--pc',HEX[c]);$('#scene').style.setProperty('--pd',shade(HEX[c],.55));
  const mine=!ONLINE||c===me.color;
  say(mode[c]==='cpu'?'(CPU) rolling…':mine?'tap the dice 🎲':'is playing…');
  $('#scene').classList.remove('six','sad');$('#scene').classList.toggle('wait',mode[c]==='human'&&mine);updSkip();
  if(mode[c]==='cpu'){const g=gen;setTimeout(()=>{if(g===gen)rollDice()},550*SP)}}
let nextRoll=0,selfRolls=0;const predicted=[];   /* nextRoll: the server told me my next number in advance */
function desync(){toast('⚠ Out of sync - reloading');try{sessionStorage.setItem('autoResume','1')}catch(e){}setTimeout(()=>location.reload(),800)}
$('#scene').onpointerdown=e=>{e.preventDefault();A();
  if(ONLINE){if(phase==='roll'&&players[cur]===me.color&&!sentRoll){sentRoll=true;
    if(nextRoll>=1&&nextRoll<=6){const v=nextRoll;nextRoll=0;selfRolls++;predicted.push(v);setTimeout(()=>{sentRoll=false},6000);post({t:'roll'});rollDice(v)}   /* dice starts at once; the server's echo only confirms it */
    else{startSpin();setTimeout(()=>{sentRoll=false;if(spinning)stopSpin()},6000);post({t:'roll'})}}return}
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
    await hammerHit(c,i,v,()=>{sfxKill();showToon('toonL',2900);flash('#ffb000');toast('🥁 Chal haat!')},()=>{v.forEach(([o,j])=>T[o][j]=-1);killed[c]=true;place()},trail);
    if(g!==gen)return;
    burst(tokEl[c][i],50,[HEX[c],'#fff','#ffd23f']);extra=true;await sleep(600);if(g!==gen)return}
  if(np===FIN_P){sfxShehnai();showToon('toonR',3500);toast('🏠 Griha Pravesh!');burst(tokEl[c][i],40);extra=true;await sleep(400)}
  if(T[c].filter(x=>x===FIN_P).length>=WINN&&!finished.includes(c)){finished.push(c);yardNames();if(finished.length===1&&!FAST)celebrate();   /* first finisher only: clip + fireworks. ranked 1st, 2nd... game goes on until one player is left */
    if(players.filter(q=>!isOut(q)).length<=1){endGame(c);return}
    toast('🏅 '+pn(c)+' finished #'+finished.length);burst(tokEl[c][i],50);await sleep(900);if(g!==gen)return;nextTurn();return}
  if(extra)startTurn();else nextTurn()}

function endGame(w0){phase='over';busy=true;gen++;clearLocal();try{localStorage.removeItem('ludoSess')}catch(e){}$('#fin').classList.add('hide');$('#quit').classList.add('hide');
  const fo=c=>{const k=finished.indexOf(c);return k<0?99:k},prog=c=>T[c].reduce((a,x)=>a+(x<0?0:x<HB?x:LAST+1+(x-HB)),0);
  const rows=players.map(c=>({c,h:T[c].filter(x=>x===FIN_P).length,p:prog(c)})).sort((a,b)=>fo(a.c)-fo(b.c)||b.h-a.h||b.p-a.p);
  if(w0&&!finished.length){const wi=rows.findIndex(r=>r.c===w0);if(wi>0)rows.unshift(rows.splice(wi,1)[0])}
  const w=rows[0].c;{const res={};players.forEach(c=>res[c]=c===w?'won':(leftSet.has(c)?'quit':'lost'));recStats(res)}if(Date.now()-clipAt>CLIP_MS+500)sfxWin();$('#wt').textContent='🏆 '+pn(w)+' wins!';$('#wt').style.color=HEX[w];
  const box=$('#rank');box.innerHTML='';
  rows.forEach((r,i)=>{const d=document.createElement('div');d.className='row';const l=document.createElement('span'),dot=document.createElement('span');
    dot.className='dot';dot.style.background=HEX[r.c];dot.style.color=HEX[r.c];l.append(dot,document.createTextNode((i+1)+'. '+pn(r.c)));
    const rr=document.createElement('span');rr.textContent=r.h+' home';d.append(l,rr);box.appendChild(d)});
  $('#win').classList.remove('hide');for(let k=0;k<5;k++)setTimeout(()=>burst($('#wt'),50),k*300)}
$('#quit').onclick=()=>{if(!confirm(ONLINE?'Quit this game? You leave your seat and the others carry on.':'Quit this game and go back to the menu?'))return;
  recQuit();
  if(ONLINE){const x={room:me.room,id:me.id};leaveOnline();api('/api/leave',x)}else clearLocal();
  gen++;phase='idle';busy=true;['#fin','#quit','#skip','#win'].forEach(q=>$(q).classList.add('hide'));
  Object.values(tokEl).flat().forEach(e=>e.remove());clearDholBoys();$('#st').textContent='';
  $('#onJoin').classList.remove('hide');$('#onLobby').classList.add('hide');$('#setup').classList.remove('hide')};
$('#fin').onclick=()=>{if(phase==='over')return;if(!confirm('Finish the game now and show the result?'))return;if(ONLINE)post({t:'finish'});else endGame()};
function saveLocal(){try{localStorage.setItem('ludoGame',JSON.stringify({players,mode,names,T,killed,cur,WINN,finished,t:Date.now()}))}catch(e){}}
function loadLocal(){try{return JSON.parse(localStorage.getItem('ludoGame')||'null')}catch(e){return null}}
function clearLocal(){try{localStorage.removeItem('ludoGame')}catch(e){}}
const isOut=c=>leftSet.has(c)||finished.includes(c);   /* quit or already finished = skipped */
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
  toast('⚠ Connection problem - resyncing');if(msg.t==='move'||(msg.t==='roll'&&selfRolls>0)){try{sessionStorage.setItem('autoResume','1')}catch(e){}setTimeout(()=>location.reload(),1200)}}
function sendMove(i){if(sentMove||phase!=='move')return;sentMove=true;setTimeout(()=>sentMove=false,6000);selfMoves++;post({t:'move',i});doMove(me.color,i)}   // moves instantly on your screen
const onErr=t=>{$('#onErr').textContent=t||''};
const inviteUrl=()=>`${BASE||location.origin}/?room=${me.room}`;
function enter(res){if(res.error){onErr(res.error);return}
  nextRoll=0;selfRolls=0;predicted.length=0;
  ONLINE=true;me={id:res.id,color:res.color,room:res.room,host:false};lastN=0;started=false;names={};
  try{localStorage.setItem('ludoSess',JSON.stringify({room:me.room,id:me.id,name:$('#pname').value.trim()}))}catch(e){}
  $('#onJoin').classList.add('hide');$('#onLobby').classList.remove('hide');$('#rc').textContent=me.room;connect()}
function connect(){pollGen++;synced=false;FAST=true;openWS(pollGen);pingLoop(pollGen)}
let wsFails=0;
function openWS(g){let opened=false,w;
  try{w=new WebSocket(`${(BASE||location.origin).replace(/^http/,'ws')}/ws?room=${me.room}&id=${me.id}&after=${lastN}`)}catch(e){ws=null;pollLoop(g);return}
  ws=w;
  const fb=setTimeout(()=>{if(!opened&&g===pollGen){try{w.close()}catch(e){}ws=null;pollLoop(g)}},4500);   // WebSocket blocked -> use long-poll instead
  w.onopen=()=>{opened=true;wsFails=0;clearTimeout(fb);onErr('')};
  w.onmessage=e=>{const d=JSON.parse(e.data);if(d.t==='pong'){gotPong(d.ts);return}if(d.t==='next'){nextRoll=d.v;return}if(d.n){if(d.n<=lastN)return;lastN=d.n}handle(d)};
  w.onclose=()=>{clearTimeout(fb);if(g!==pollGen||!ONLINE||ws!==w)return;ws=null;if(opened){onErr('Reconnecting…');setTimeout(()=>{if(g===pollGen&&ONLINE)openWS(g)},Math.min(600*2**wsFails++,8000))}}}
const rs=ms=>new Promise(r=>setTimeout(r,ms));
const RTT=[];
function showNet(ms){const e=$('#net');e.classList.remove('hide');e.textContent=(ms<200?'🟢 ':ms<400?'🟡 ':'🔴 ')+ms+' ms'}
function gotPong(ts){RTT.push(Math.round(performance.now()-ts));if(RTT.length>5)RTT.shift();showNet([...RTT].sort((a,b)=>a-b)[RTT.length>>1])}   /* median of the last 5 = steady number */
async function pingLoop(g){
  while(g===pollGen&&ONLINE){
    if(document.hidden){await rs(4000);continue}
    if(ws&&ws.readyState===1){try{ws.send(JSON.stringify({t:'ping',ts:performance.now()}))}catch(x){}await rs(4000);continue}   /* real game-connection round trip, no HTTP/TLS overhead */
    const t=performance.now();
    try{await fetch(BASE+'/health',{cache:'no-store'});showNet(Math.round(performance.now()-t))}   /* long-poll fallback only */
    catch(x){const e=$('#net');e.classList.remove('hide');e.textContent='🔴 offline'}
    await rs(10000)}
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
    }catch(e){if(g!==pollGen)return;fails++;onErr('Reconnecting…');await rs(Math.min(700*fails,8000))}}}
function handle(d){
  if(d.t==='lobby'){names={};Object.entries(d.seats).forEach(([c,n])=>names[c]=n);Object.assign(gameNames,names);me.host=d.host===me.color;lobbySeats=d.seats;lobbyHost=d.host;renderLobby();if(started&&phase!=='over')$('#fin').classList.toggle('hide',!me.host)}
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
const SETTLED=()=>(phase==='roll'&&!busy)||phase==='move'||phase==='over'||phase==='idle';
async function runQ(){qrun=true;
  while(MQ.length){BACKLOG=MQ.length;const m=MQ.shift();
    if(m.t==='roll'){if(m.c===me.color&&selfRolls>0){selfRolls--;sentRoll=false;if(predicted.shift()!==m.v)desync();continue}   /* my own roll, already shown */
      if(!await until(SETTLED,40000)||phase!=='roll'||m.c!==players[cur])continue;sentRoll=false;await rollDice(m.v)}
    else if(m.t==='move'){if(m.c===me.color&&selfMoves>0){selfMoves--;sentMove=false;continue}
      if(!await until(SETTLED,40000)||phase!=='move')continue;const c=players[cur];if(m.c!==c)continue;sentMove=false;
      if(!(m.i>=0&&m.i<4)||stepsList(c,T[c][m.i],roll)===null)continue;await doMove(c,m.i)}
    else if(m.t==='skip'){if(await until(()=>phase==='roll'&&!busy))nextTurn()}
    else if(m.t==='left'){leftSet.add(m.c);yardNames();const alive=players.filter(c=>!isOut(c));
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
if(/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1))document.body.classList.add('ios');
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
async function loadSrvStats(){const el=$('#srvStat');try{const r=await fetch(BASE+'/api/stats',{cache:'no-store'});const d=await r.json();
  el.textContent=`Online now: ${d.online}  ·  Games running: ${d.rooms}/${d.max_rooms}  ·  Total visits: ${Number(d.visits).toLocaleString()}`+(d.full?'  ·  Server full: new rooms paused':'')}catch(e){el.textContent=''}}
try{if(!sessionStorage.getItem('hit')){sessionStorage.setItem('hit','1');fetch(BASE+'/api/hit',{method:'POST'}).catch(()=>{})}}catch(e){}
loadSrvStats();setInterval(()=>{if(!document.hidden&&!$('#setup').classList.contains('hide'))loadSrvStats()},20000);
$('#mkRoom').onclick=async()=>{const n=$('#pname').value.trim();if(!n){onErr('Enter your name first');return}saveProfile(n);onErr('');enter(await api('/api/create',{name:n}))};
$('#joinRoom').onclick=async()=>{const n=$('#pname').value.trim(),r=$('#rcode').value.trim().toUpperCase();
  if(!n||r.length<4){onErr('Enter your name and the 4-letter room code');return}saveProfile(n);onErr('');
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
  $('#rsErr').textContent='';$('#resume').classList.add('hide');$('#online').classList.remove('hide');$('#pname').value=s.name||getProfile();enter(res)}
function resumeOffline(){const g=loadLocal();if(!g)return;players=g.players;mode=g.mode;names=g.names||{};WINN=g.WINN||4;$('#resume').classList.add('hide');$('#setup').classList.add('hide');A();newGame(g)}
$('#rsOnGo').onclick=resumeOnline;
$('#rsOnX').onclick=async()=>{const s=store();if(s)await api('/api/leave',{room:s.room,id:s.id});try{localStorage.removeItem('ludoSess')}catch(e){}$('#rsErr').textContent='';refreshResume()};
$('#rsOffGo').onclick=resumeOffline;
$('#rsOffX').onclick=()=>{clearLocal();refreshResume()};
$('#rsNew').onclick=()=>{$('#resume').classList.add('hide');$('#setup').classList.remove('hide')};
(function(){const q=(new URLSearchParams(location.search).get('room')||'').toUpperCase();
  if(!q){if(sessionStorage.getItem('autoResume')==='1'){sessionStorage.removeItem('autoResume');if(store()){showResume();resumeOnline();return}}showResume();return}
  const s=store();
  $('#setup').classList.add('hide');$('#online').classList.remove('hide');$('#rcode').value=q;$('#pname').value=(s&&s.name)||getProfile();
  if(s&&s.room===q&&s.id&&s.name)api('/api/join',{name:s.name,room:q,id:s.id}).then(enter)})();

if('serviceWorker' in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('/sw.js').catch(()=>{});
</script></body></html>
"""


# ============================================================================
# 2. ASSETS (icons are base64 PNGs)
# ============================================================================
ICON192 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAADlElEQVR42u3dPXITQRRFYWlKGyCmKLMBHJHDBvBOCL0EIjLYBhErIIdIRIQExCzBBEpE2WD9jKbf7f5OaE1Zre4z9/VUy8/ruzdvV/g31x+fmYT/MJkCEAgEAoFAIIBAIBAIBAIBBAKBQCAQCCAQCAQCgUAAgUAgEAgEAoEAAoFAIBAIBBAIBAKBQCCAQCAQCAQCAQQCgUAgpLNJGuznD8u/57bRZ73++T5iTdbV2/y2kKYalWUqLBB1EjQqKRB1cjSa2JPF9uqWQOzpx6EyJYw6meVsYo8o6msPhCgKCCR+kkNoYg+HYgViT75D9kAIFUj8dBFCEgiJAomfXkJIAoFAaMcm/QM8ffLy/g9//f5mtMvQ4jB1pg3Qg4tRdmEWG+3CJ6ypJezR9TjwGqMdroQdNdG7ixtGUdZobaJBoAvkfKvqkDXa/gU6Z2aXX5Ws0SphINCFb8olb+us0UogEAgEAoEAAoFAINDMnH9CtOQZU9ZoJRAIdOGbcvkbOmu0oyTQaTPbaj2yRquEoQF5Xyjb3aAHHhU1v5uzRjtQAh0y13XWI2u0nSfQITd3wcXIGu0QAiXOfrQrNtEgEAgEAgEEgqewy9Hf8zaBWqqz/xKNlLBT7DnqGglEnccvFkUSCARaPH7UMgLN5gGHCAQCNYofIUQgEAhN2azebc1CTzz/uug/PJBAIBAIBAJFMk4XBAKBQN2FkAN5Ap3uAXsIhHPxhbK/4qTjLggSqEotY48EOjGKqEMgG2QlDAQCgQACgUDwFHYWWc/beiRWX4z9l0otTK89G6b+7DnqGqMdLoGyuiB037PBJhojCZTVBWGEng1T9/a0WpVBejYoYRhDoKwuCOP0bJBAIBAIBAKBQACBQKAHyOqCME7PBgmEYQTK6oIwSM+GsATK6oIwQs8GJQxnkfeFsqwuCN33bEhNoKwuCB33bFjfbV81eNsXX+b6Tf4qY5+bT0pY11vO/no22ESDQBhOoO+vTf3sLL8BkkDIFUgI5cePBEK0QEIoPH4KJBCHku2pUcI4FGuPPRD6EEgIZcbPqtBZ2M6h+Q5ZqTNkCRNFUfaU3ANxKMeeVdGvcyhnCeoUFohGCeqUF+h+RRtJpsrSRAnUent080MEZm2iQSAQCCAQCAQCgUAAgUAgEAgEAggEAoFAIBAIBBAIBAKBQCCAQCAQCAQCAQQCgUAgEAggEAgEAoFAAIFAIBAIBMKI/AEzQkJZyJ8zLQAAAABJRU5ErkJggg==")
WIN_MP3 = base64.b64decode("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3CiiQaBI2OUHJ1wdseIh7BKRPYmCpHJT1/cfWyp4Bbcs60r/+p09/ltVBAkoKAugu1QUAM3DoyBIuHZyy7QejamrVrppR3nZQ0VaCjnNhhYqbWYB4T0dwLFCzfwUNDo+v1mG7bR1bWuVhm2tVWPri+p6hrJAUTB07ng0JXKApWVyoaiMFe48q8lvDTcOvYW5adO2kIokKDCMsQ02C9MLbJwCWRIonEqIqdGH60sM//tIxK8ADl2FTSekS8GbEWjk8yFgOAiaA0mOxr0KCAjy1oCJmqkGEYSeeOw0RWqDRIOQ1EWoCij3ndh36tYaY/X//bnfr4Nf6Wfx/yz/POVMQU1FMy4xMDBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVU9H2lMQU1FMy4xMDBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//tIxLWBDSThOMexA4FVj+RM8wyoVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//tIxI2DwFgCAA4AACAAADSAAAAEVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV")    # first-winner clip (mono mp3, ~9.7 s)
CHAL_MP3 = base64.b64decode("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")    # "Chal haat" voice (kill)
DHOL_MP3 = base64.b64decode("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")    # dhol (token leaves the yard)
ICON512 = base64.b64decode("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")


MANIFEST = json.dumps({
    "name": "Glass Ludo", "short_name": "Glass Ludo", "start_url": "/", "scope": "/",
    "display": "standalone", "orientation": "portrait",
    "background_color": "#1b0b3a", "theme_color": "#1b0b3a",
    "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
              {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]})

# Network-first cache for the page itself. API calls, the WebSocket and /health are never cached
# (caching /health made the "offline" indicator lie).
SW = ("self.addEventListener('install',e=>self.skipWaiting());"
      "self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));"
      "self.addEventListener('fetch',e=>{const u=new URL(e.request.url);"
      "if(e.request.method!=='GET'||u.origin!==location.origin||u.pathname.startsWith('/api/')"
      "||u.pathname==='/health'||u.pathname==='/ws')return;"
      "e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open('gl').then(k=>k.put(e.request,c));return r})"
      ".catch(()=>caches.match(e.request)))});")

REVALIDATE = "no-cache"                     # browser keeps a copy but re-checks it: a tiny 304 when unchanged
LONG_CACHE = "public, max-age=604800"       # icons and sounds never change: keep for a week


def _asset(body, ctype, cache):
    """A cacheable file with a (weak) ETag so repeat visits cost a few hundred bytes instead of the whole file."""
    body = body.encode("utf-8") if isinstance(body, str) else body
    return {"body": body, "type": ctype,
            "headers": {"ETag": 'W/"%s"' % hashlib.sha1(body).hexdigest()[:16], "Cache-Control": cache}}


STATIC = {"/manifest.json": _asset(MANIFEST, "application/manifest+json", REVALIDATE),
          "/sw.js": _asset(SW, "application/javascript", REVALIDATE),
          "/icon-192.png": _asset(ICON192, "image/png", LONG_CACHE),
          "/icon-512.png": _asset(ICON512, "image/png", LONG_CACHE),
          "/a/chal.mp3": _asset(CHAL_MP3, "audio/mpeg", LONG_CACHE),
          "/a/dhol.mp3": _asset(DHOL_MP3, "audio/mpeg", LONG_CACHE),
          "/a/win.mp3": _asset(WIN_MP3, "audio/mpeg", LONG_CACHE)}
PAGE = _asset(HTML, "text/html; charset=utf-8", REVALIDATE)
PAGE_GZ = gzip.compress(PAGE["body"], 9)    # compressed once at start-up, not per request


# ============================================================================
# 3. ROOM  (one online game)
# ============================================================================
COLORS = ["red", "green", "yellow", "blue"]
OPPOSITE = {"red": "yellow", "yellow": "red", "green": "blue", "blue": "green"}
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOM_TTL = 6 * 3600                 # a started game with nobody connected is dropped after 6 hours
LOBBY_TTL = 30 * 60                 # a room nobody started is dropped after 30 minutes
ACTIVE_WINDOW = 15 * 60             # a room counts as "running" if someone is connected or it moved in the last 15 min
# Capacity limit: new rooms are refused once this many games are running (players already in a room are never kicked).
# Measured: 100 rooms (400 players) uses <1% of a CPU core and ~45 MB; override with the MAX_ROOMS environment variable.
MAX_ROOMS = int(os.environ.get("MAX_ROOMS", 100))
VISIT_GAP = 30 * 60                 # same visitor (IP) within 30 minutes counts as one visit
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
ROOMS_FILE = os.environ.get("ROOMS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ludo_rooms.json"))

STATS_FILE = os.environ.get("STATS_FILE", os.path.join(os.path.dirname(ROOMS_FILE), "ludo_stats.json"))
STATS = {"visits": 0, "today": 0, "day": "", "since": int(time.time())}
STATS_LOCK = threading.Lock()
VISITORS = {}                       # ip -> time of last counted visit

COMPACT = (",", ":")                # compact JSON: fewer bytes on the wire

RNG = random.SystemRandom()         # the server rolls the dice, so nobody can cheat
ROOMS = {}
ROOMS_LOCK = threading.Lock()       # guards the ROOMS dict only; never held while a Room lock is taken
SAVE_EVERY = 5                      # seconds between disk saves (a background thread; games never wait for it)
_dirty = threading.Event()


class Room:
    """Server picks dice values and relays every action to all players, in order.

    `log` is the single source of truth: a reconnecting client just replays it.
    All mutable state is protected by `lock` (re-entrant); `cond` wakes long-pollers.
    """

    def __init__(self, code):
        self.code = code
        self.seats = {}             # colour -> client id
        self.names = {}             # client id -> display name
        self.host = None            # client id of the host
        self.started = False
        self.log = []               # ordered game messages (dicts)
        self.logj = []              # the same messages, already encoded as JSON text (sent / saved as-is)
        self.next = {}              # colour -> that player's NEXT dice value (chosen now, told only to that player)
        self.rev = 0                # bumped on every change; lets the saver skip rooms that did not change
        self._saved = (-1, "")      # (rev, json text) of the last save of this room
        self.conns = {}             # client id -> [Queue, ...] (open WebSockets)
        self.left = set()           # colours that quit mid-game
        self.seen = {}              # client id -> last long-poll time
        self.touch = time.time()
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)

    def is_active(self, now=None):
        now = now or time.time()
        return bool(self.conns) or now - self.touch < ACTIVE_WINDOW

    # ---- seats ----
    def color_of(self, cid):
        return next((c for c, i in self.seats.items() if i == cid), None)

    def lobby(self):
        return {"t": "lobby", "host": self.color_of(self.host),
                "seats": {c: self.names[i] for c, i in self.seats.items()}}

    def free_corner(self):
        """Prefer the corner opposite an existing player (2 players = diagonal), else the first free one."""
        for c in self.seats:
            if OPPOSITE[c] not in self.seats:
                return OPPOSITE[c]
        return next((c for c in COLORS if c not in self.seats), None)

    # ---- messaging ----
    def deal(self, color):
        """Pick this player's next dice value in advance and tell ONLY them. Their roll can then land the instant they
        tap instead of waiting a network round trip. The server still decides the number; nobody else sees it."""
        v = self.next[color] = RNG.randint(1, 6)
        self.rev += 1
        for q in self.conns.get(self.seats.get(color), []):
            q.put('{"t":"next","v":%d}' % v)

    def _fanout(self, raw):
        for queues in self.conns.values():
            for q in queues:
                q.put(raw)

    def append(self, msg):
        """Add a message to the log and push it to everyone."""
        with self.lock:
            msg["n"] = len(self.log) + 1
            raw = json.dumps(msg, separators=COMPACT)
            self.log.append(msg)
            self.logj.append(raw)
            self.rev += 1
            self.touch = time.time()
            self.cond.notify_all()
            self._fanout(raw)
        schedule_save()

    def transient(self, msg):
        """Push a message that is not stored in the log (e.g. presence)."""
        with self.lock:
            self._fanout(json.dumps(msg, separators=COMPACT))

    def online_colors(self):
        now = time.time()
        with self.lock:
            return [c for c, i in self.seats.items() if i in self.conns or now - self.seen.get(i, 0) < 35]

    def presence(self):
        self.transient({"t": "presence", "on": self.online_colors()})

    # ---- WebSocket connections ----
    def attach(self, cid, after):
        """Register a live connection; returns its queue, pre-filled with everything after `after`."""
        q = queue.Queue()
        with self.lock:
            for raw in self.logj[after:]:
                q.put(raw)
            q.put('{"t":"synced"}')
            col = self.color_of(cid)
            if self.started and col:                      # (re)connecting player gets their current next value
                if col not in self.next:
                    self.next[col] = RNG.randint(1, 6)
                    self.rev += 1
                q.put('{"t":"next","v":%d}' % self.next[col])
            self.conns.setdefault(cid, []).append(q)
            self.seen[cid] = time.time()
        return q

    def detach(self, cid, q):
        with self.lock:
            qs = self.conns.get(cid, [])
            if q in qs:
                qs.remove(q)
            if not qs:
                self.conns.pop(cid, None)
                self.seen[cid] = 0          # closed connection = offline now (not 35 s later)


# ---- persistence (games survive a server restart where the disk is kept) ----
def schedule_save():
    _dirty.set()                    # just raises a flag; the saver thread does the work later


def _saver():
    """Background thread: save at most every SAVE_EVERY seconds, and only if something changed."""
    while True:
        _dirty.wait()
        time.sleep(SAVE_EVERY)
        _dirty.clear()
        _do_save()


def _room_json(r):
    """JSON text of one room. Re-encoded only when the room changed; the log reuses the already-encoded messages."""
    with r.lock:
        if r._saved[0] != r.rev:
            text = '{"seats":%s,"names":%s,"host":%s,"started":%s,"touch":%s,"left":%s,"next":%s,"log":[%s]}' % (
                json.dumps(r.seats), json.dumps(r.names), json.dumps(r.host), "true" if r.started else "false",
                r.touch, json.dumps(sorted(r.left)), json.dumps(r.next), ",".join(r.logj))
            r._saved = (r.rev, text)
        return r._saved[1]


def _do_save():
    try:
        with ROOMS_LOCK:
            items = list(ROOMS.items())
        body = "{" + ",".join("%s:%s" % (json.dumps(code), _room_json(r)) for code, r in items) + "}"
        tmp = ROOMS_FILE + ".tmp"
        with open(tmp, "w") as f:
            f.write(body)
        os.replace(tmp, ROOMS_FILE)
        _save_stats()
    except Exception:
        pass


def _save_stats():
    with STATS_LOCK:
        data = dict(STATS)
    tmp = STATS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, STATS_FILE)


def load_stats():
    try:
        with open(STATS_FILE) as f:
            STATS.update({k: v for k, v in json.load(f).items() if k in STATS})
    except Exception:
        pass


def count_visit(ip):
    """Count one visit per visitor (IP) per VISIT_GAP, not every reload (called by the page's /api/hit beacon)."""
    now = time.time()
    if now - VISITORS.get(ip, 0) < VISIT_GAP:
        return
    VISITORS[ip] = now
    if len(VISITORS) > 5000:
        for k in [k for k, t in VISITORS.items() if now - t > VISIT_GAP]:
            VISITORS.pop(k, None)
    day = time.strftime("%Y-%m-%d")
    with STATS_LOCK:
        if STATS["day"] != day:
            STATS["day"], STATS["today"] = day, 0
        STATS["visits"] += 1
        STATS["today"] += 1
    schedule_save()


def purge_rooms():
    """Drop abandoned rooms so they do not use up capacity."""
    now = time.time()
    with ROOMS_LOCK:
        for k, r in list(ROOMS.items()):
            idle = now - r.touch
            if not r.conns and (idle > ROOM_TTL or (not r.started and idle > LOBBY_TTL)):
                del ROOMS[k]


_stats_memo = (0.0, None)


def server_stats(max_age=3):
    """Live numbers for the home screen. Cached for a few seconds so many phones polling cost almost nothing."""
    global _stats_memo
    now = time.time()
    if max_age and _stats_memo[1] and now - _stats_memo[0] < max_age:
        return _stats_memo[1]
    purge_rooms()
    rooms = list(ROOMS.values())
    running = sum(1 for r in rooms if r.is_active(now))
    with STATS_LOCK:
        visits, today = STATS["visits"], STATS["today"]
    out = {"visits": visits, "today": today, "online": sum(len(r.online_colors()) for r in rooms),
           "rooms": running, "max_rooms": MAX_ROOMS, "full": running >= MAX_ROOMS}
    _stats_memo = (now, out)
    return out


def load_rooms():
    try:
        with open(ROOMS_FILE) as f:
            data = json.load(f)
    except Exception:
        return
    now = time.time()
    for code, d in data.items():
        if now - d.get("touch", 0) > ROOM_TTL:
            continue
        r = Room(code)
        r.seats, r.names, r.host = d["seats"], d["names"], d["host"]
        r.started, r.log, r.touch = d["started"], d["log"], now
        r.logj = [json.dumps(m, separators=COMPACT) for m in r.log]
        r.rev = 1
        r.left = set(d.get("left", []))
        r.next = d.get("next", {})
        ROOMS[code] = r


# ============================================================================
# 4. API  (every function takes the decoded JSON body and returns a dict)
# ============================================================================
def clean_name(n):
    return " ".join(str(n or "").split())[:14] or "Player"


def new_id():
    return os.urandom(8).hex()


def new_code():
    return "".join(RNG.choice(CODE_CHARS) for _ in range(4))


def find_room(code):
    return ROOMS.get(str(code or "").strip().upper())


def api_create(d):
    purge_rooms()
    if server_stats(0)["full"] or len(ROOMS) > MAX_ROOMS * 5:
        return {"error": f"Server is full ({MAX_ROOMS} games running). Please try again in a few minutes."}
    with ROOMS_LOCK:
        code = new_code()
        while code in ROOMS:
            code = new_code()
        r = ROOMS[code] = Room(code)
    cid = new_id()
    with r.lock:
        r.seats["red"] = cid
        r.names[cid] = clean_name(d.get("name"))
        r.host = cid
        r.seen[cid] = time.time()
        r.append(r.lobby())
    return {"id": cid, "color": "red", "room": code}


def api_join(d):
    r = find_room(d.get("room"))
    if not r:
        return {"error": "Room not found - check the code"}
    cid = str(d.get("id") or "")
    with r.lock:
        if cid and cid in r.names:                        # re-join after refresh / reconnect
            col = r.color_of(cid)
            if col in r.left:
                return {"error": "You left this game"}
            return {"id": cid, "color": col, "room": r.code}
        if r.started:
            return {"error": "That game has already started"}
        col = r.free_corner()
        if col is None:
            return {"error": "Room is full (4 players)"}
        cid = new_id()
        r.seats[col] = cid
        r.names[cid] = clean_name(d.get("name"))
        r.append(r.lobby())
    return {"id": cid, "color": col, "room": r.code}


def api_leave(d):
    """Close this device's session. Before the game starts the seat is freed (host leaving closes the room)."""
    r = find_room(d.get("room"))
    cid = str(d.get("id") or "")
    if not r or cid not in r.names:
        return {"ok": True}
    close_room = False
    with r.lock:
        col = r.color_of(cid)
        if not r.started:
            if cid == r.host:
                r.append({"t": "closed"})
                close_room = True
            else:
                if col:
                    del r.seats[col]
                del r.names[cid]
                r.seen.pop(cid, None)
                r.append(r.lobby())
        elif col and col not in r.left:                   # game running: tell everyone this player left
            r.left.add(col)
            if cid == r.host:                             # hand "host" to someone still playing
                r.host = next((i for c, i in r.seats.items() if c not in r.left), r.host)
                r.append(r.lobby())
            r.append({"t": "left", "c": col})
    if close_room:                                        # taken after the room lock is released (no nested locks)
        with ROOMS_LOCK:
            ROOMS.pop(r.code, None)
        schedule_save()
    return {"ok": True}


def api_send(d):
    r = find_room(d.get("room"))
    cid = str(d.get("id", ""))
    msg = d.get("msg")
    if not r or r.color_of(cid) is None:
        return {"error": "not in room"}
    if not isinstance(msg, dict):
        return {"ok": True}
    t = msg.get("t")
    with r.lock:
        color = r.color_of(cid)
        if t == "seat" and not r.started:
            new = msg.get("color")
            if new in COLORS and new != color:
                if new in r.seats:
                    return {"error": "That corner is taken"}
                del r.seats[color]
                r.seats[new] = cid
                r.append(r.lobby())
                return {"ok": True, "color": new}
            return {"ok": True, "color": color}
        if t == "start":
            if cid == r.host and not r.started and len(r.seats) >= 2:
                r.started = True
                w = msg.get("win")
                r.append({"t": "start", "win": w if isinstance(w, int) and 1 <= w <= 4 else 4,
                          "players": [c for c in COLORS if c in r.seats]})
                for c in list(r.seats):
                    r.deal(c)
        elif not r.started:
            pass
        elif t == "roll":
            v = r.next.pop(color, None) or RNG.randint(1, 6)   # the value this player was already told
            r.append({"t": "roll", "c": color, "v": v})
            r.deal(color)                                        # and the one after it
        elif t == "move":
            i = msg.get("i")
            if isinstance(i, int) and 0 <= i < 4:
                r.append({"t": "move", "c": color, "i": i})
        elif t in ("skip", "finish") and cid == r.host:
            r.append({"t": t})
    return {"ok": True}


# ============================================================================
# 5. HTTP + WEBSOCKET
# ============================================================================
def _arg(q, key, default=""):
    return q.get(key, [default])[0]


def _after(q):
    try:
        return max(0, int(_arg(q, "after", "0")))
    except ValueError:
        return 0


def ws_frame(op, payload=b""):
    """Build one unmasked server->client WebSocket frame."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    n = len(payload)
    if n < 126:
        head = bytes([0x80 | op, n])
    elif n < 65536:
        head = bytes([0x80 | op, 126]) + struct.pack(">H", n)
    else:
        head = bytes([0x80 | op, 127]) + struct.pack(">Q", n)
    return head + payload


def ws_unmask(payload, mask):
    """XOR payload with the 4-byte mask (done as one big-int XOR instead of a Python loop per byte)."""
    n = len(payload)
    if not n:
        return payload
    key = (mask * (n // 4 + 1))[:n]
    return (int.from_bytes(payload, "big") ^ int.from_bytes(key, "big")).to_bytes(n, "big")


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "GlassLudo"
    protocol_version = "HTTP/1.1"       # keep-alive: faster repeated requests
    timeout = 70

    def setup(self):
        super().setup()
        try:
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # send small packets immediately
        except OSError:
            pass

    def log_message(self, *a):
        pass

    # ---- responses ----
    def _send(self, code, body=b"", ctype="application/json", extra=None):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        headers = {"Cache-Control": "no-store", "Access-Control-Allow-Origin": "*"}
        headers.update(extra or {})
        if code != 304:                                   # 304 = "you already have it": headers only
            headers.update({"Content-Type": ctype, "Content-Length": str(len(b))})
        self.send_response(code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        if code != 304 and self.command != "HEAD":
            self.wfile.write(b)

    def _serve(self, asset, gz=None):
        """Send a cacheable file (gzip if the browser accepts it), or just a 304 if its copy is current."""
        headers = dict(asset["headers"], Vary="Accept-Encoding")
        if asset["headers"]["ETag"] in [t.strip() for t in self.headers.get("If-None-Match", "").split(",")]:
            return self._send(304, extra=headers)
        if gz and "gzip" in self.headers.get("Accept-Encoding", ""):
            return self._send(200, gz, asset["type"], dict(headers, **{"Content-Encoding": "gzip"}))
        self._send(200, asset["body"], asset["type"], headers)

    def _client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or self.client_address[0]

    # ---- routing ----
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        if p in ("/", "/index.html"):
            return self._serve(PAGE, PAGE_GZ)
        if p in STATIC:
            return self._serve(STATIC[p])
        if p == "/health":
            return self._send(200, "ok", "text/plain")
        if p == "/api/stats":
            return self._send(200, json.dumps(server_stats()))
        if p == "/ws":
            return self.ws(q)
        if p == "/api/poll":
            return self.poll(q)
        self._send(404, "not found", "text/plain")

    do_HEAD = do_GET                                      # uptime monitors usually ping with HEAD

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") == "/api/hit":    # one real browser visit (bots / pingers never run JS)
            count_visit(self._client_ip())
            return self._send(200, '{"ok":true}')
        routes = {"/api/create": api_create, "/api/join": api_join, "/api/send": api_send, "/api/leave": api_leave}
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
        except Exception:
            return self._send(400, '{"error":"bad request"}')
        fn = routes.get(urlparse(self.path).path.rstrip("/"))
        if not fn:
            return self._send(404, '{"error":"not found"}')
        self._send(200, json.dumps(fn(data)))

    # ---- long-poll transport (fallback when WebSockets are blocked) ----
    def poll(self, q):
        """Wait (up to 20 s) until there is a new message, then answer immediately."""
        r, cid = find_room(_arg(q, "room")), _arg(q, "id")
        if not r or cid not in r.names:
            return self._send(200, '{"error":"unknown room"}')
        after = _after(q)
        deadline = time.time() + 20
        with r.cond:
            r.seen[cid] = time.time()
            while len(r.log) <= after:
                left = deadline - time.time()
                if left <= 0:
                    break
                r.cond.wait(min(left, 5))
                r.seen[cid] = time.time()
            msgs = ",".join(r.logj[after:after + 300])
            more = len(r.log) > after + 300
        self._send(200, '{"msgs":[%s],"more":%s,"on":%s}' % (msgs, "true" if more else "false", json.dumps(r.online_colors())))

    # ---- WebSocket transport ----
    def ws_read(self):
        """Read one complete WebSocket message (or control frame) from the client."""
        f = self.rfile

        def need(n):
            b = f.read(n)
            if b is None or len(b) < n:
                raise OSError("closed")
            return b

        data, first_op = b"", None
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
                payload = ws_unmask(payload, mask)
            if op >= 8:                                   # control frame (close / ping / pong)
                return op, payload
            if first_op is None:
                first_op = op
            data += payload
            if fin:
                return first_op, data

    def ws(self, q):
        """One always-open connection; messages are pushed instantly both ways."""
        r, cid = find_room(_arg(q, "room")), _arg(q, "id")
        key = self.headers.get("Sec-WebSocket-Key")
        if not r or cid not in r.names or not key:
            return self._send(404, '{"error":"unknown room"}')
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.close_connection = True
        sock = self.connection
        sock.settimeout(75)
        send_lock, alive = threading.Lock(), threading.Event()
        alive.set()

        def send_raw(data):
            with send_lock:
                sock.sendall(data)

        def send(op, payload=b""):
            send_raw(ws_frame(op, payload))

        qu = r.attach(cid, _after(q))
        r.presence()

        def writer():
            try:
                while alive.is_set():
                    try:
                        item = qu.get(timeout=20)
                    except queue.Empty:
                        send(9)                           # keep-alive ping
                        continue
                    frames = []
                    while item is not None:                   # send everything that is already waiting in ONE write
                        frames.append(ws_frame(1, item))
                        if len(frames) >= 64:
                            break
                        try:
                            item = qu.get_nowait()
                        except queue.Empty:
                            break
                    if frames:
                        send_raw(b"".join(frames))
                    if item is None:
                        break
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
                    if isinstance(msg, dict) and msg.get("t") == "ping":     # latency meter: answer at once, never queued
                        send(1, '{"t":"pong","ts":%s}' % json.dumps(msg.get("ts")))
                        continue
                    api_send({"room": r.code, "id": cid, "msg": msg})
        except (OSError, ValueError):
            pass
        finally:
            alive.clear()
            qu.put(None)
            r.detach(cid, qu)
            r.presence()
            try:
                send(8)
            except OSError:
                pass


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 256            # default is 5: bursts of reconnecting phones were refused

    def handle_error(self, request, client_address):
        pass                                              # ignore dropped phone connections quietly


# ============================================================================
# 6. MAIN
# ============================================================================
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
    sys.setswitchinterval(0.002)                          # let a waiting player's thread run sooner under load
    load_rooms()
    load_stats()
    threading.Thread(target=_saver, daemon=True).start()
    hosted = "PORT" in os.environ                         # cloud hosts give a PORT
    port = int(os.environ.get("PORT", 8000))
    while True:
        try:
            srv = Server(("0.0.0.0", port), Handler)
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
    signal.signal(signal.SIGTERM, lambda *_: (_do_save(), os._exit(0)))   # hosts stop the app with SIGTERM: keep games + stats
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        _do_save()
        print("\nBye!")


if __name__ == "__main__":
    main()
