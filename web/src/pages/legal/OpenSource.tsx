import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const packages = [
  // Frontend
  { name: 'React', version: '18.x', license: 'MIT', url: 'https://github.com/facebook/react' },
  { name: 'Vite', version: '6.x', license: 'MIT', url: 'https://github.com/vitejs/vite' },
  { name: 'TailwindCSS', version: '4.x', license: 'MIT', url: 'https://github.com/tailwindlabs/tailwindcss' },
  { name: 'React Router', version: '7.x', license: 'MIT', url: 'https://github.com/remix-run/react-router' },
  { name: 'lucide-react', version: 'latest', license: 'ISC', url: 'https://github.com/lucide-icons/lucide' },
  { name: 'react-markdown', version: 'latest', license: 'MIT', url: 'https://github.com/remarkjs/react-markdown' },
  { name: 'react-dropzone', version: 'latest', license: 'MIT', url: 'https://github.com/react-dropzone/react-dropzone' },
  { name: 'remark-gfm', version: 'latest', license: 'MIT', url: 'https://github.com/remarkjs/remark-gfm' },
  { name: 'Socket.IO Client', version: '4.x', license: 'MIT', url: 'https://github.com/socketio/socket.io' },
  // Node.js Backend
  { name: 'Express', version: '4.x', license: 'MIT', url: 'https://github.com/expressjs/express' },
  { name: 'Socket.IO', version: '4.x', license: 'MIT', url: 'https://github.com/socketio/socket.io' },
  { name: 'ioredis', version: '5.x', license: 'MIT', url: 'https://github.com/redis/ioredis' },
  { name: 'cors', version: '2.x', license: 'MIT', url: 'https://github.com/expressjs/cors' },
  { name: 'dotenv', version: '16.x', license: 'BSD-2-Clause', url: 'https://github.com/motdotla/dotenv' },
  // Python AI Backend
  { name: 'FastAPI', version: 'latest', license: 'MIT', url: 'https://github.com/fastapi/fastapi' },
  { name: 'uvicorn', version: 'latest', license: 'BSD-3-Clause', url: 'https://github.com/encode/uvicorn' },
  { name: 'python-multipart', version: 'latest', license: 'Apache-2.0', url: 'https://github.com/Kludex/python-multipart' },
  { name: 'openai (Python)', version: 'latest', license: 'Apache-2.0', url: 'https://github.com/openai/openai-python' },
  { name: 'pdfplumber', version: 'latest', license: 'MIT', url: 'https://github.com/jsvine/pdfplumber' },
  { name: 'python-dotenv', version: 'latest', license: 'BSD-3-Clause', url: 'https://github.com/theskumar/python-dotenv' },
  { name: 'pydantic', version: 'latest', license: 'MIT', url: 'https://github.com/pydantic/pydantic' },
  // Infrastructure
  { name: 'Nginx', version: 'alpine', license: 'BSD-2-Clause', url: 'https://nginx.org/' },
  { name: 'Redis', version: '7.x', license: 'BSD-3-Clause / RSALv2', url: 'https://github.com/redis/redis' },
  { name: 'Node.js', version: '20.x', license: 'MIT', url: 'https://nodejs.org/' },
  { name: 'Python', version: '3.11', license: 'PSF License', url: 'https://www.python.org/' },
];

export default function OpenSource() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] mb-8 transition-colors">
        <ArrowLeft className="h-4 w-4" /> 返回首页
      </Link>

      <h1 className="text-3xl font-bold mb-3">开源声明</h1>
      <p className="text-[var(--color-text-secondary)] mb-8">
        本项目基于以下开源软件构建。我们感谢所有开源社区的贡献者。
      </p>

      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left px-4 py-3 font-semibold text-[var(--color-text-primary)]">软件名称</th>
                <th className="text-left px-4 py-3 font-semibold text-[var(--color-text-primary)]">版本</th>
                <th className="text-left px-4 py-3 font-semibold text-[var(--color-text-primary)]">许可证</th>
                <th className="text-left px-4 py-3 font-semibold text-[var(--color-text-primary)]">链接</th>
              </tr>
            </thead>
            <tbody>
              {packages.map((pkg) => (
                <tr key={pkg.name} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-medium text-[var(--color-text-primary)]">{pkg.name}</td>
                  <td className="px-4 py-3 text-[var(--color-text-secondary)]">{pkg.version}</td>
                  <td className="px-4 py-3">
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-[var(--color-accent)]/15 text-[var(--color-accent-light)]">
                      {pkg.license}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <a href={pkg.url} target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent-light)] hover:underline">
                      查看源码
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="mt-6 text-sm text-[var(--color-text-secondary)]">
        所有依赖均采用允许商业使用的开源协议（MIT、Apache-2.0、BSD、ISC 等）。
        如发现协议相关问题，请联系我们。
      </p>
    </div>
  );
}
