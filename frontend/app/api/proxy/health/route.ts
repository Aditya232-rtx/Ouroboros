// API Proxy - Health check endpoint
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET() {
    try {
        const response = await fetch(`${BACKEND_URL}/health`);
        // Handle non-JSON responses
        const ct = response.headers.get('content-type') || '';
        if (!ct.includes('application/json')) {
            const text = await response.text();
            return Response.json(
                { status: 'error', message: text || 'Backend returned non-JSON response' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Health proxy error:', error);
        return Response.json(
            { status: 'error', message: 'Backend unreachable' },
            { status: 503 }
        );
    }
}
