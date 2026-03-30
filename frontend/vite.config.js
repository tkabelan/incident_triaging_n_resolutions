import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    var backendOrigin = env.VITE_BACKEND_ORIGIN || "http://127.0.0.1:8001";
    return {
        plugins: [react()],
        server: {
            port: 5173,
            proxy: {
                "/api": {
                    target: backendOrigin,
                    changeOrigin: true,
                },
            },
        },
    };
});
