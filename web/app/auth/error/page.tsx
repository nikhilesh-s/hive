import Link from 'next/link';

export default function AuthError() {
  return <section style={{ padding: '40px 24px' }}>
    <h1>Sign-in could not be completed</h1>
    <p>Please try Continue with Google again.</p>
    <Link href="/">Return to HiveBlot</Link>
  </section>;
}
