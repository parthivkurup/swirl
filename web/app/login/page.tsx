import LoginForm from "./LoginForm";

export const metadata = { title: "Admin login" };

export default function LoginPage() {
  return (
    <main className="mx-auto max-w-sm p-6">
      <h1 className="text-2xl font-semibold">Reviewer login</h1>
      <p className="mt-1 text-sm text-neutral-500">The review queue is admin only.</p>
      <LoginForm />
    </main>
  );
}
