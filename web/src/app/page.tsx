export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">Recourse</h1>
      <p className="mt-3 text-base">
        A coverage denial becomes a case, and the case works itself. Front end
        scaffolded Oct 26, 2026; the product is built from Oct 27.
      </p>
      <p className="mt-6 text-sm opacity-70">
        API: <code>{process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}</code>
      </p>
    </main>
  );
}
