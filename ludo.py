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

File layout
 1. HTML        - the whole game client (HTML + CSS + JS, one string)
 2. Assets      - icons, manifest, service worker
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
import socket
import struct
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
.yn{position:absolute;left:50%;top:50%;width:140%;transform:translate(-50%,-50%) rotate(-45deg);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;pointer-events:none;
 font-size:calc(var(--bs)*var(--fs,.05));font-weight:800;line-height:1.15;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.4);
 text-shadow:-.04em -.04em .03em rgba(0,0,0,.34),.05em .05em .03em rgba(255,255,255,.8)}   /* embossed: dark edge top-left, light edge bottom-right */
.yn .a{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.yn .b{font-size:.6em;letter-spacing:.22em}
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
  <div style="font-size:13px;opacity:.9">Choose corners, player type and a name for each human player (shown in their start box)</div>
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
function A(){if(!AC){try{unlockAud()}catch(err){}AC=new(window.AudioContext||window.webkitAudioContext)();OUT=AC.createGain();OUT.gain.value=2.4;
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
function synthDhol(){boost=2.4;const t=now(),P='dttdtdttddtdttdt';for(let i=0;i<P.length;i++)dholHit(t+i*.15,P[i]);boost=1}
/* "Chal haat!" - voice taken from your video, slowed to 80% (pitch kept) so it is not too fast */
const CHAL_SRC='data:audio/mpeg;base64,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';
/* ----- recorded sounds (all embedded, work offline). Volume of each can be changed below ----- */
const DHOL_OUT_SRC='data:audio/mpeg;base64,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';    /* your dhol clip, 2.8 s, plays when a goti leaves the yard */
const VOL_DHOL_OUT=.85,VOL_CHAL=1;   /* dhol only when a goti leaves the yard; kill = Chal haat voice only */
const AUD={},AUDSRC={chal:CHAL_SRC,dout:DHOL_OUT_SRC};
function getAud(k){if(!AUD[k]){AUD[k]=new Audio(AUDSRC[k]);AUD[k].preload='auto'}return AUD[k]}
function unlockAud(){Object.keys(AUDSRC).forEach(k=>{try{const a=getAud(k);a.muted=true;const pr=a.play();   /* first tap unlocks sounds on phones */
  if(pr&&pr.then)pr.then(()=>{a.pause();a.currentTime=0;a.muted=false}).catch(()=>{a.muted=false});else{a.pause();a.muted=false}}catch(err){}})}
function playAud(k,vol,fail){if(muted||FAST)return;try{const a=getAud(k);a.pause();a.currentTime=0;a.volume=vol;const pr=a.play();if(pr&&pr.catch)pr.catch(()=>fail&&fail())}catch(err){fail&&fail()}}
function voiceMaara(){playAud('chal',VOL_CHAL,ttsChal)}
function sfxDholOut(){playAud('dout',VOL_DHOL_OUT,synthDholOut)}
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
function yardNames(){COLORS.forEach(c=>{const e=yardNm[c];if(!e)return;const on=players.includes(c),k=finished.indexOf(c),n=on?pn(c):'';   /* player name (diagonal, embossed) in own start box + finishing place */
  e.a.textContent=n;e.b.textContent=on&&k>=0?PLACE[k]:'';e.box.style.setProperty('--fs',Math.min(.06,.42/Math.max(n.length,5)));e.box.style.opacity=on&&leftSet.has(c)?.5:1})}
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
    await hammerHit(c,i,v,()=>{sfxKill();showToon('toonL',2900);flash('#ffb000');toast('🥁 Chal haat!')},()=>{v.forEach(([o,j])=>T[o][j]=-1);killed[c]=true;place()},trail);
    if(g!==gen)return;
    burst(tokEl[c][i],50,[HEX[c],'#fff','#ffd23f']);extra=true;await sleep(600);if(g!==gen)return}
  if(np===FIN_P){sfxShehnai();showToon('toonR',3500);toast('🏠 Griha Pravesh!');burst(tokEl[c][i],40);extra=true;await sleep(400)}
  if(T[c].filter(x=>x===FIN_P).length>=WINN&&!finished.includes(c)){finished.push(c);yardNames();   /* ranked 1st, 2nd... game goes on until one player is left */
    if(players.filter(q=>!isOut(q)).length<=1){endGame(c);return}
    toast('🏅 '+pn(c)+' finished #'+finished.length);burst(tokEl[c][i],50);await sleep(900);if(g!==gen)return;nextTurn();return}
  if(extra)startTurn();else nextTurn()}

function endGame(w0){phase='over';busy=true;gen++;clearLocal();try{localStorage.removeItem('ludoSess')}catch(e){}$('#fin').classList.add('hide');$('#quit').classList.add('hide');
  const fo=c=>{const k=finished.indexOf(c);return k<0?99:k},prog=c=>T[c].reduce((a,x)=>a+(x<0?0:x<HB?x:LAST+1+(x-HB)),0);
  const rows=players.map(c=>({c,h:T[c].filter(x=>x===FIN_P).length,p:prog(c)})).sort((a,b)=>fo(a.c)-fo(b.c)||b.h-a.h||b.p-a.p);
  if(w0&&!finished.length){const wi=rows.findIndex(r=>r.c===w0);if(wi>0)rows.unshift(rows.splice(wi,1)[0])}
  const w=rows[0].c;{const res={};players.forEach(c=>res[c]=c===w?'won':(leftSet.has(c)?'quit':'lost'));recStats(res)}sfxWin();$('#wt').textContent='🏆 '+pn(w)+' wins!';$('#wt').style.color=HEX[w];
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
    if(m.t==='roll'){if(!await until(SETTLED,40000)||phase!=='roll'||m.c!==players[cur])continue;sentRoll=false;await rollDice(m.v)}
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

STATIC = {"/manifest.json": (MANIFEST, "application/manifest+json"),
          "/sw.js": (SW, "application/javascript"),
          "/icon-192.png": (ICON192, "image/png"),
          "/icon-512.png": (ICON512, "image/png"),
          "/health": ("ok", "text/plain")}

HTML_BYTES = HTML.encode("utf-8")
HTML_GZ = gzip.compress(HTML_BYTES, 9)      # compressed once at start-up, not per request


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

RNG = random.SystemRandom()         # the server rolls the dice, so nobody can cheat
ROOMS = {}
ROOMS_LOCK = threading.Lock()       # guards the ROOMS dict only; never held while a Room lock is taken
_save_pending = False


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
        self.log = []               # ordered game messages
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
    def _fanout(self, msg):
        for queues in self.conns.values():
            for q in queues:
                q.put(msg)

    def append(self, msg):
        """Add a message to the log and push it to everyone."""
        with self.lock:
            msg["n"] = len(self.log) + 1
            self.log.append(msg)
            self.touch = time.time()
            self.cond.notify_all()
            self._fanout(msg)
        schedule_save()

    def transient(self, msg):
        """Push a message that is not stored in the log (e.g. presence)."""
        with self.lock:
            self._fanout(msg)

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
            for m in self.log[after:]:
                q.put(m)
            q.put({"t": "synced"})
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
    """Coalesce writes: at most one disk save every 1.5 s."""
    global _save_pending
    if _save_pending:
        return
    _save_pending = True
    threading.Timer(1.5, _do_save).start()


def _do_save():
    global _save_pending
    _save_pending = False
    try:
        with ROOMS_LOCK:
            items = list(ROOMS.items())
        data = {}
        for code, r in items:
            with r.lock:
                data[code] = {"seats": dict(r.seats), "names": dict(r.names), "host": r.host, "started": r.started,
                              "log": list(r.log), "touch": r.touch, "left": list(r.left)}
        tmp = ROOMS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
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
    """Count one visit per visitor (IP) per VISIT_GAP, not every reload."""
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


def server_stats():
    purge_rooms()
    now = time.time()
    rooms = list(ROOMS.values())
    running = sum(1 for r in rooms if r.is_active(now))
    with STATS_LOCK:
        visits, today = STATS["visits"], STATS["today"]
    return {"visits": visits, "today": today, "online": sum(len(r.online_colors()) for r in rooms),
            "rooms": running, "max_rooms": MAX_ROOMS, "full": running >= MAX_ROOMS}


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
        r.left = set(d.get("left", []))
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
    if server_stats()["full"] or len(ROOMS) > MAX_ROOMS * 5:
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
        elif not r.started:
            pass
        elif t == "roll":
            r.append({"t": "roll", "c": color, "v": RNG.randint(1, 6)})
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
    def _send(self, code, body, ctype="application/json", extra=None):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def _client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or self.client_address[0]

    def _page(self):
        count_visit(self._client_ip())
        if "gzip" in self.headers.get("Accept-Encoding", ""):
            return self._send(200, HTML_GZ, "text/html; charset=utf-8",
                              {"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
        self._send(200, HTML_BYTES, "text/html; charset=utf-8", {"Vary": "Accept-Encoding"})

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
            return self._page()
        if p in STATIC:
            return self._send(200, *STATIC[p])
        if p == "/api/stats":
            return self._send(200, json.dumps(server_stats()))
        if p == "/ws":
            return self.ws(q)
        if p == "/api/poll":
            return self.poll(q)
        self._send(404, "not found", "text/plain")

    def do_POST(self):
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
            msgs = r.log[after:after + 300]
            more = len(r.log) > after + 300
        self._send(200, json.dumps({"msgs": msgs, "more": more, "on": r.online_colors()}))

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

        def send(op, payload=b""):
            frame = ws_frame(op, payload)
            with send_lock:
                sock.sendall(frame)

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
                    if item is None:
                        break
                    send(1, json.dumps(item))
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
    load_rooms()
    load_stats()
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
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")


if __name__ == "__main__":
    main()
