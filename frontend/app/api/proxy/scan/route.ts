// API Proxy - Main scan endpoint
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const cookieHeader = request.headers.get('cookie') || '';

        const response = await fetch(`${BACKEND_URL}/scan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cookie': cookieHeader,
            },
            body: JSON.stringify(body),
        });

        // Handle non-JSON responses
        const ct = response.headers.get('content-type') || '';
        if (!ct.includes('application/json')) {
            const text = await response.text();
            return Response.json(
                { detail: text || 'Backend returned non-JSON response' },
                { status: response.status }
            );
        }

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
        const cookieHeader = request.headers.get('cookie') || '';
        const response = await fetch(`${BACKEND_URL}/scan`, {
            headers: { 'Cookie': cookieHeader },
        });
        // Handle non-JSON responses
        const ct = response.headers.get('content-type') || '';
        if (!ct.includes('application/json')) {
            const text = await response.text();
            return Response.json(
                { detail: text || 'Backend returned non-JSON response' },
                { status: response.status }
            );
        }

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
