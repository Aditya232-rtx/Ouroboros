// API Proxy - Status endpoint
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(
    request: Request,
    { params }: { params: { scanId: string } }
) {
    try {
        const { scanId } = params;
        const url = new URL(request.url);
        const endpoint = url.pathname.replace('/api/proxy/status/', '/status/');

        const response = await fetch(`${BACKEND_URL}${endpoint}`);

        if (!response.ok && response.status === 404) {
            return Response.json(
                { detail: 'Not found' },
                { status: 404 }
            );
        }

        const data = await response.json();
        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Status proxy error:', error);
        return Response.json(
            { detail: 'Failed to fetch status' },
            { status: 500 }
        );
    }
}
