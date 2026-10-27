// WhatsApp do usuário como "aparelho conectado" (Baileys, o mesmo motor da Evolution API).
//   node whatsapp.mjs conectar              gera qr.png para escanear no celular (só na 1ª vez)
//   node whatsapp.mjs grupos                lista os grupos (id e nome) para escolher o de vendas
//   node whatsapp.mjs enviar <arquivo.txt>  manda o texto para o grupo salvo em config.json
//   node whatsapp.mjs enviar <arquivo.txt> --para <id>   manda para outro destino (teste)
import { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, Browsers } from "baileys";
import QRCode from "qrcode";
import pino from "pino";
import { readFileSync, existsSync, rmSync } from "node:fs";
import { exec } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const PASTA = path.dirname(fileURLToPath(import.meta.url));
const SESSAO = process.env.WA_SESSAO || path.join(PASTA, "sessao");          // chaves do aparelho conectado: não copiar para lugar nenhum
const CONFIG = process.env.WA_CONFIG || path.join(PASTA, "config.json");      // {"grupo": "1203...@g.us"}
const [, , comando, arquivo, ...resto] = process.argv;

function conectar() {
  return new Promise(async (resolve, reject) => {
    const { state, saveCreds } = await useMultiFileAuthState(SESSAO);
    const { version } = await fetchLatestBaileysVersion();
    const sock = makeWASocket({
      auth: state, version, logger: pino({ level: "silent" }),
      browser: Browsers.windows("Ranking UFit"),
      markOnlineOnConnect: false,   // não deixa o celular "online" nem tira as notificações dele
      syncFullHistory: false,
    });
    sock.ev.on("creds.update", saveCreds);
    sock.ev.on("connection.update", async ({ connection, lastDisconnect, qr }) => {
      if (qr) {
        if (comando !== "conectar") return reject(new Error("WhatsApp desconectado: rode 'node whatsapp.mjs conectar'"));
        const png = path.join(PASTA, "qr.png");
        await QRCode.toFile(png, qr, { width: 400 });
        console.log("Escaneie o QR: WhatsApp > Aparelhos conectados > Conectar aparelho. Arquivo:", png);
        if (process.platform === "win32") exec(`start "" "${png}"`);
      }
      if (connection === "open") resolve(sock);
      if (connection === "close") {
        const codigo = lastDisconnect?.error?.output?.statusCode;
        if (codigo === DisconnectReason.restartRequired) return resolve(conectar());  // normal logo após escanear
        if (codigo === DisconnectReason.loggedOut) {
          rmSync(SESSAO, { recursive: true, force: true });
          return reject(new Error("O aparelho foi desconectado no celular: rode 'node whatsapp.mjs conectar' de novo"));
        }
        reject(lastDisconnect?.error || new Error("Conexão fechada"));
      }
    });
  });
}

const fim = async (sock, codigo = 0) => { await new Promise(r => setTimeout(r, 3000)); sock.end(undefined); process.exit(codigo); };

try {
  if (!["conectar", "grupos", "enviar"].includes(comando)) {
    console.log("Uso: node whatsapp.mjs conectar | grupos | enviar <arquivo.txt> [--para <id>]");
    process.exit(1);
  }
  const sock = await conectar();
  if (comando === "conectar") {
    console.log("Conectado como", sock.user?.name || sock.user?.id);
    await fim(sock);
  } else if (comando === "grupos") {
    const grupos = Object.values(await sock.groupFetchAllParticipating());
    grupos.sort((a, b) => a.subject.localeCompare(b.subject));
    for (const g of grupos) console.log(`${g.id}\t${g.subject}`);
    await fim(sock);
  } else {
    const i = resto.indexOf("--para");
    const destino = i >= 0 ? resto[i + 1] : (existsSync(CONFIG) ? JSON.parse(readFileSync(CONFIG, "utf8")).grupo : null);
    if (!destino) throw new Error("Falta o grupo em config.json");
    const texto = readFileSync(arquivo, "utf8").trim();
    await sock.sendMessage(destino, { text: texto });
    console.log("Enviado para", destino);
    await fim(sock);
  }
} catch (e) {
  console.error("Erro:", e.message);
  process.exit(1);
}
