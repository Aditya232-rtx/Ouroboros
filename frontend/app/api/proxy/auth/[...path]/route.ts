// API Proxy - Auth endpoints (login, signup, logout, me, refresh)
const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function POST(request: Request) {
    try {
        const url = new URL(request.url);
        const endpoint = url.pathname.replace('/api/proxy/auth/', '/auth/');

        // Forward cookies from the incoming request
        const cookieHeader = request.headers.get('cookie') || '';

        let body: string | undefined;
        const contentType = request.headers.get('content-type');
        if (contentType?.includes('application/json')) {
            body = JSON.stringify(await request.json());
        }

        const response = await fetch(`${BACKEND_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cookie': cookieHeader,
            },
            body,
        });

        // Handle non-JSON responses
        const respContentType = response.headers.get('content-type') || '';
        if (!respContentType.includes('application/json')) {
            const text = await response.text();
            const fallbackRes = Response.json(
                { detail: text || 'Backend returned non-JSON response' },
                { status: response.status }
            );
            // Still forward Set-Cookie headers even on error
            const setCookiesErr = response.headers.getSetCookie?.() || [];
            const headersErr = new Headers(fallbackRes.headers);
            for (const cookie of setCookiesErr) {
                headersErr.append('Set-Cookie', cookie);
            }
            return new Response(fallbackRes.body, {
                status: response.status,
                headers: headersErr,
            });
        }

        const data = await response.json();

        // Forward Set-Cookie headers from backend to browser
        const res = Response.json(data, { status: response.status });
        const setCookies = response.headers.getSetCookie?.() || [];
        const headers = new Headers(res.headers);
        for (const cookie of setCookies) {
            headers.append('Set-Cookie', cookie);
        }

        return new Response(res.body, {
            status: response.status,
            headers,
        });
    } catch (error) {
        console.error('Auth proxy error:', error);
        return Response.json(
            { detail: 'Failed to proxy auth request' },
            { status: 500 }
        );
    }
}

export async function GET(request: Request) {
    try {
        const url = new URL(request.url);
        const endpoint = url.pathname.replace('/api/proxy/auth/', '/auth/');

        // Forward cookies from the incoming request
        const cookieHeader = request.headers.get('cookie') || '';

        const response = await fetch(`${BACKEND_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                'Cookie': cookieHeader,
            },
        });

        // Handle non-JSON responses
        const respCt = response.headers.get('content-type') || '';
        if (!respCt.includes('application/json')) {
            const text = await response.text();
            return Response.json(
                { detail: text || 'Backend returned non-JSON response' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return Response.json(data, { status: response.status });
    } catch (error) {
        console.error('Auth proxy error:', error);
        return Response.json(
            { detail: 'Failed to proxy auth request' },
            { status: 500 }
        );
    }
}
