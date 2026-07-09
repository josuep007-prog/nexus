// ---------------------------------------------------------------------------
// CSRF: injeta o token (meta[name=csrf]) como campo oculto em TODO formulário
// POST — assim nenhum template precisa lembrar de incluir o campo na mão.
// ---------------------------------------------------------------------------
function tokenCsrf() {
    const meta = document.querySelector('meta[name="csrf"]');
    return meta ? meta.content : "";
}

document.addEventListener("DOMContentLoaded", () => {
    const token = tokenCsrf();
    if (token) {
        document.querySelectorAll('form[method="post" i]').forEach((form) => {
            if (!form.querySelector('input[name="_csrf"]')) {
                const campo = document.createElement("input");
                campo.type = "hidden";
                campo.name = "_csrf";
                campo.value = token;
                form.appendChild(campo);
            }
        });
    }
});

// ---------------------------------------------------------------------------
// Push do PWA: pede permissão e registra a inscrição no servidor.
// Chamado pelo botão "Ativar notificações" na página Minha conta.
// ---------------------------------------------------------------------------
async function ativarPush(botao) {
    const aviso = (txt) => { if (botao) botao.textContent = txt; };
    try {
        const resp = await fetch("/push/chave-publica");
        const cfg = await resp.json();
        if (!cfg.ativo) { aviso("Push não configurado no servidor"); return; }
        const registro = await navigator.serviceWorker.ready;
        const permissao = await Notification.requestPermission();
        if (permissao !== "granted") { aviso("Permissão negada no navegador"); return; }
        const assinatura = await registro.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: base64ParaUint8(cfg.chave),
        });
        const r = await fetch("/push/inscrever", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF": tokenCsrf() },
            body: JSON.stringify(assinatura.toJSON()),
        });
        aviso(r.ok ? "✓ Notificações ativadas neste dispositivo" : "Falha ao registrar");
    } catch (erro) {
        console.warn("Push:", erro);
        aviso("Não foi possível ativar");
    }
}

function base64ParaUint8(base64) {
    const padding = "=".repeat((4 - (base64.length % 4)) % 4);
    const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
    const bruto = atob(b64);
    return Uint8Array.from([...bruto].map((c) => c.charCodeAt(0)));
}

// Dropzone de upload de arquivo (atestados, admissões)
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".dropzone").forEach((dropzone) => {
        const input = dropzone.querySelector("input[type=file]");
        const nomeArquivo = dropzone.querySelector(".nome-arquivo");

        const atualizarNomes = (arquivos) => {
            if (!arquivos || arquivos.length === 0) {
                nomeArquivo.textContent = "";
            } else if (arquivos.length === 1) {
                nomeArquivo.textContent = "Selecionado: " + arquivos[0].name;
            } else {
                const nomes = Array.from(arquivos).map(f => f.name).join(", ");
                nomeArquivo.textContent = arquivos.length + " arquivos selecionados: " + nomes;
            }
        };

        dropzone.addEventListener("click", () => input.click());
        input.addEventListener("change", () => atualizarNomes(input.files));

        ["dragenter", "dragover"].forEach(evento => {
            dropzone.addEventListener(evento, (e) => {
                e.preventDefault();
                dropzone.classList.add("arrastando");
            });
        });
        ["dragleave", "drop"].forEach(evento => {
            dropzone.addEventListener(evento, (e) => {
                e.preventDefault();
                dropzone.classList.remove("arrastando");
            });
        });
        dropzone.addEventListener("drop", (e) => {
            if (e.dataTransfer.files.length > 0) {
                input.files = e.dataTransfer.files;
                atualizarNomes(input.files);
            }
        });
    });

    // Auto-esconder mensagens flash depois de um tempo
    document.querySelectorAll(".flash").forEach((el, i) => {
        setTimeout(() => {
            el.style.transition = "opacity 0.4s ease";
            el.style.opacity = "0";
            setTimeout(() => el.remove(), 400);
        }, 6000 + i * 300);
    });
});
