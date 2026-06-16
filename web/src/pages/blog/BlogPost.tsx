import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock, Tag } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import blogs from '../../data/blogs.json';

interface BlogData {
  slug: string;
  title: string;
  summary: string;
  tags: string[];
  date: string;
  readTime: string;
  content: string;
}

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>();
  const post = (blogs as BlogData[]).find((b) => b.slug === slug);

  if (!post) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <h1 className="text-2xl font-bold mb-4">文章不存在</h1>
        <p className="text-[var(--color-text-secondary)] mb-6">找不到对应的博客文章</p>
        <Link to="/blog" className="btn-primary inline-flex items-center gap-2 px-5 py-2.5">
          <ArrowLeft className="h-4 w-4" /> 返回列表
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <Link
        to="/blog"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent-light)] mb-8 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> 返回博客列表
      </Link>

      <article>
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-[var(--color-text-primary)] mb-4">
            {post.title}
          </h1>
          <div className="flex flex-wrap items-center gap-4 text-sm text-[var(--color-text-secondary)]">
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              {post.date}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              {post.readTime}
            </span>
          </div>
          <div className="flex flex-wrap gap-2 mt-4">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-white/5 text-[var(--color-accent-light)] border border-white/10"
              >
                <Tag className="h-3 w-3" />
                {tag}
              </span>
            ))}
          </div>
        </header>

        {/* Content */}
        <div className="prose prose-invert prose-lg max-w-none
          prose-headings:text-[var(--color-text-primary)]
          prose-p:text-[var(--color-text-secondary)]
          prose-a:text-[var(--color-accent-light)]
          prose-strong:text-[var(--color-text-primary)]
          prose-code:text-[var(--color-accent-light)] prose-code:bg-white/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
          prose-pre:bg-[var(--color-bg-secondary)] prose-pre:border prose-pre:border-white/10 prose-pre:rounded-xl
          prose-li:text-[var(--color-text-secondary)]
        ">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {post.content}
          </ReactMarkdown>
        </div>
      </article>
    </div>
  );
}
