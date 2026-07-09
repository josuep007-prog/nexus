// sw.js — Service Worker do Automação DP
// Objetivo principal: tornar o app instalável no Android (Chrome exige um
// service worker registrado pra mostrar o prompt "Adicionar à tela inicial").
// Cache é propositalmente simples: só o "shell" estático (CSS/JS/ícones).
// As páginas (solicitações, validações etc.) sempre buscam da rede, porque
// os dados mudam o tempo todo — cachear isso daria informação desatualizada.

const CACHE_NAME = "automacao-dp-shell-v4";
const ARQUIVOS_SHELL = [
    "/static/style.css",
    "/static/app.js",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png",
];

self.addEventListener("install", (evento) => {
    evento.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ARQUIVOS_SHELL))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
    evento.waitUntil(
        caches.keys().then((nomes) =>
            Promise.all(
                nomes.filter((nome) => nome !== CACHE_NAME).map((nome) => caches.delete(nome))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
    const url = new URL(evento.request.url);

    // Só intercepta os arquivos estáticos do shell — cache first, com fallback pra rede.
    if (url.pathname.startsWith("/static/")) {
        evento.respondWith(
            caches.match(evento.request).then((resposta) => resposta || fetch(evento.request))
        );
        return;
    }

    // Todo o resto (páginas com dados) vai direto pra rede, sem cache.
});

// ---------------------------------------------------------------------------
// Push: mostra a notificação mesmo com o app fechado (Android/PWA).
// O payload vem do servidor (utils/notificacoes.py): {titulo, corpo, url}.
// ---------------------------------------------------------------------------
self.addEventListener("push", (evento) => {
    let dados = { titulo: "Automação DP", corpo: "Você tem uma novidade.", url: "/" };
    try {
        dados = { ...dados, ...evento.data.json() };
    } catch (_e) { /* payload vazio ou não-JSON: usa o padrão */ }
    evento.waitUntil(
        self.registration.showNotification(dados.titulo, {
            body: dados.corpo,
            icon: "/static/icons/icon-192.png",
            badge: "/static/icons/icon-192.png",
            data: { url: dados.url },
        })
    );
});

self.addEventListener("notificationclick", (evento) => {
    evento.notification.close();
    const url = (evento.notification.data && evento.notification.data.url) || "/";
    evento.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then((janelas) => {
            for (const janela of janelas) {
                if ("focus" in janela) {
                    janela.navigate(url);
                    return janela.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});
