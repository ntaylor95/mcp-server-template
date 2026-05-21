export interface AskResponse {
  answer: string;
  source: { name: string; url: string } | null;
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `Server error ${res.status}`);
  }

  return res.json();
}
