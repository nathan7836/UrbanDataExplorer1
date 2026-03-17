(function () {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get('api');
    const fromEnv = window.__UDE_API_BASE__;
    const servedByApi = window.location.pathname.startsWith('/dashboard');
    window.API_BASE_URL =
        fromQuery ||
        fromEnv ||
        (servedByApi ? window.location.origin : 'http://localhost:8001');
})();
