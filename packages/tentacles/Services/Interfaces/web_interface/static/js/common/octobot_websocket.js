/*
 * Drakkar-Software OctoBot
 * Copyright (c) Drakkar-Software, All rights reserved.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3.0 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.
 */

function getWebSocketBasePath(){
    const meta = document.querySelector('meta[name="octobot-web-socket-base-path"]');
    if(meta && meta.content){
        return meta.content.replace(/\/$/, "");
    }
    return "";
}

function OctoBotWebSocket(namespace){
    const eventHandlers = {};
    let webSocket = null;
    let intentionalClose = false;
    let reconnectTimer = null;
    const namespacePath = namespace.startsWith("/") ? namespace : `/${namespace}`;
    const webSocketProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const webSocketUrl = `${webSocketProtocol}//${window.location.host}${getWebSocketBasePath()}${namespacePath}`;

    function dispatchEvent(eventName, data){
        const handlers = eventHandlers[eventName];
        if(!handlers){
            return;
        }
        handlers.forEach((handler) => handler(data));
    }

    function connect(){
        webSocket = new WebSocket(webSocketUrl);
        webSocket.onmessage = (messageEvent) => {
            try{
                const payload = JSON.parse(messageEvent.data);
                if(payload && typeof payload.event === "string"){
                    dispatchEvent(payload.event, payload.data);
                }
            }catch(error){
                console.error("Invalid WebSocket message", error);
            }
        };
        webSocket.onclose = () => {
            dispatchEvent("disconnect");
            if(!intentionalClose){
                reconnectTimer = setTimeout(connect, 2000);
            }
        };
        webSocket.onerror = () => {
            dispatchEvent("disconnect");
        };
    }

    connect();

    return {
        on(eventName, handler){
            if(!eventHandlers[eventName]){
                eventHandlers[eventName] = [];
            }
            eventHandlers[eventName].push(handler);
        },
        off(eventName, handler){
            const handlers = eventHandlers[eventName];
            if(!handlers){
                return;
            }
            eventHandlers[eventName] = handlers.filter((registeredHandler) => registeredHandler !== handler);
        },
        emit(eventName, data){
            if(webSocket && webSocket.readyState === WebSocket.OPEN){
                webSocket.send(JSON.stringify({event: eventName, data: data}));
            }
        },
        disconnect(){
            intentionalClose = true;
            if(reconnectTimer){
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            if(webSocket){
                webSocket.close();
            }
        },
    };
}

function get_websocket(namespace){
    return new OctoBotWebSocket(namespace);
}
