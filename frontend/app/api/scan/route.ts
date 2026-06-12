// Next.js API route to proxy requests to backend
// This allows the frontend to work with a single ngrok tunnel

const API_BASE_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function POST(request: Request) {
    try {
        const body = await request.json();

        const response = await fetch(`${API_BASE_URL}/scan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        const data = await response.json();

        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Proxy error:', error);
        return Response.json(
            { error: 'Failed to proxy request' },
            { status: 500 }
        );
    }
}
