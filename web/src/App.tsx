import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './layouts/Layout';
import HomePage from './pages/HomePage';
import BlogList from './pages/blog/BlogList';
import BlogPost from './pages/blog/BlogPost';
import AIChat from './pages/ai/AIChat';
import KnowledgeList from './pages/knowledge/KnowledgeList';
import KnowledgeDetail from './pages/knowledge/KnowledgeDetail';
import OpenSource from './pages/legal/OpenSource';
import Privacy from './pages/legal/Privacy';
import Terms from './pages/legal/Terms';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/blog" element={<BlogList />} />
          <Route path="/blog/:slug" element={<BlogPost />} />
          <Route path="/ai" element={<AIChat />} />
          <Route path="/knowledge" element={<KnowledgeList />} />
          <Route path="/knowledge/:id" element={<KnowledgeDetail />} />
          <Route path="/open-source" element={<OpenSource />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
