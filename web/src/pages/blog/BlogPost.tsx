import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock, Tag } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import posts, { type BlogPost as BlogPostData } from '../../data/blogs-loader';

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>();
  const post = posts.find((b) => b.slug === slug) as BlogPostData | undefined;

  if (!post) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <h1 className="text-2xl font-bold mb-4">文章不存在</h1>
        <p className="text-[var(--color-text-secondary)] mb-6">找不到对应的博客文章</p>
        <Link to="/blog" className="btn-primary">
          <ArrowLeft className="h-4 w-4" /> 返回列表
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:py-14">
      <Link
        to="/blog"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> 返回博客列表
      </Link>

      <article>
        <header className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text)] mb-3">
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
          <div className="flex flex-wrap gap-1.5 mt-3">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
              >
                <Tag className="h-3 w-3" />
                {tag}
              </span>
            ))}
          </div>
        </header>

        <div
          style={{ maxWidth: 'none' }}
          className="prose-sm sm:prose
            prose-headings:text-[var(--color-text)]
            prose-p:text-[var(--color-text-secondary)]
            prose-a:text-[var(--color-accent)]
            prose-strong:text-[var(--color-text)]
            prose-code:text-[var(--color-accent)] prose-code:bg-[var(--color-bg-muted)] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
            prose-pre:bg-[var(--color-bg-muted)] prose-pre:border prose-pre:border-[var(--color-border)] prose-pre:rounded-xl
            prose-table:text-[var(--color-text-secondary)]
            prose-li:text-[var(--color-text-secondary)]
          "
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {post.content}
          </ReactMarkdown>
        </div>
      </article>
    </div>
  );
}
