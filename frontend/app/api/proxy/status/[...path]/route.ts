// API Proxy - Status endpoint
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(
    request: Request,
    { params }: { params: Promise<{ path: string[] }> }
) {
    try {
        const { path } = await params;
        const endpoint = `/status/${path.join('/')}`;
        const cookieHeader = request.headers.get('cookie') || '';

        const response = await fetch(`${BACKEND_URL}${endpoint}`, {
            headers: { 'Cookie': cookieHeader },
        });

        if (!response.ok && response.status === 404) {
            return Response.json(
                { detail: 'Not found' },
                { status: 404 }
            );
        }

        // Handle non-JSON responses (e.g. backend returns plain text error)
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            const text = await response.text();
            return Response.json(
                { detail: text || 'Backend returned non-JSON response' },
                { status: response.status }
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
