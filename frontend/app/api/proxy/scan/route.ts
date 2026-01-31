// API Proxy - Main scan endpoint
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function POST(request: Request) {
    try {
        const body = await request.json();

        const response = await fetch(`${BACKEND_URL}/scan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        const data = await response.json();
        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Scan proxy error:', error);
        return Response.json(
            { detail: 'Failed to proxy scan request' },
            { status: 500 }
        );
    }
}

export async function GET(request: Request) {
    try {
        const response = await fetch(`${BACKEND_URL}/scan`);
        const data = await response.json();
        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Scan list proxy error:', error);
        return Response.json(
            { detail: 'Failed to fetch scans' },
            { status: 500 }
        );
    }
}
