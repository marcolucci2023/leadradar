import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-white">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center font-bold text-sm">
            LR
          </div>
          <span className="text-xl font-bold">LeadRadar</span>
        </div>
        <div className="flex gap-4">
          <Link
            href="/login"
            className="px-4 py-2 text-sm text-slate-300 hover:text-white transition"
          >
            Connexion
          </Link>
          <Link
            href="/login"
            className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
          >
            Commencer gratuitement
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-8 pt-20 pb-32 text-center">
        <div className="inline-block px-4 py-1 mb-6 text-xs font-medium bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30">
          Le Harvey AI du commerce local
        </div>
        <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
          Trouvez vos prochains
          <br />
          <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            clients locaux
          </span>
        </h1>
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10">
          LeadRadar cherche, enrichit et score automatiquement les commerces
          locaux de n&apos;importe quelle ville du monde. Messages de prospection
          personnalisés par IA en un clic.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/login"
            className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-lg font-semibold transition shadow-lg shadow-indigo-500/25"
          >
            Lancer une recherche →
          </Link>
          <a
            href="#features"
            className="px-8 py-4 border border-slate-700 hover:border-slate-500 rounded-xl text-lg transition"
          >
            En savoir plus
          </a>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-8 max-w-lg mx-auto mt-20">
          <div>
            <div className="text-3xl font-bold text-indigo-400">28+</div>
            <div className="text-sm text-slate-500">Types de commerces</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-cyan-400">195</div>
            <div className="text-sm text-slate-500">Pays couverts</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-emerald-400">IA</div>
            <div className="text-sm text-slate-500">Scoring intelligent</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-7xl mx-auto px-8 py-20">
        <h2 className="text-3xl font-bold text-center mb-16">
          Tout-en-un pour votre prospection
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="p-8 bg-slate-800/50 rounded-2xl border border-slate-700/50">
            <div className="w-12 h-12 bg-indigo-500/20 rounded-xl flex items-center justify-center text-2xl mb-4">
              🔍
            </div>
            <h3 className="text-xl font-semibold mb-2">Recherche mondiale</h3>
            <p className="text-slate-400">
              Trouvez restaurants, dentistes, garages et plus dans n&apos;importe
              quelle ville du monde via OpenStreetMap.
            </p>
          </div>
          <div className="p-8 bg-slate-800/50 rounded-2xl border border-slate-700/50">
            <div className="w-12 h-12 bg-cyan-500/20 rounded-xl flex items-center justify-center text-2xl mb-4">
              🤖
            </div>
            <h3 className="text-xl font-semibold mb-2">Scoring IA</h3>
            <p className="text-slate-400">
              Notre IA analyse chaque lead et lui attribue un score de 0 à 100
              selon son besoin en digitalisation.
            </p>
          </div>
          <div className="p-8 bg-slate-800/50 rounded-2xl border border-slate-700/50">
            <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center text-2xl mb-4">
              ✉️
            </div>
            <h3 className="text-xl font-semibold mb-2">Messages personnalisés</h3>
            <p className="text-slate-400">
              Générez des emails de prospection sur mesure en français, arabe ou
              anglais, prêts à envoyer.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center py-12 text-slate-600 text-sm border-t border-slate-800">
        © 2026 LeadRadar. Tous droits réservés.
      </footer>
    </div>
  );
}