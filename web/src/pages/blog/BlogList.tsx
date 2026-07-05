import { Link } from 'react-router-dom';
import { Calendar, Clock, Tag } from 'lucide-react';
import posts from '../../data/blogs-loader';

export default function BlogList() {
  // 已按日期降序排列（在 loader 中处理）
  const sortedPosts = posts;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:py-14">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text)] mb-2">技术博客</h1>
        <p className="text-[var(--color-text-secondary)] text-sm">深度技术文章，记录学习与实践</p>
      </div>

      <div className="grid gap-4">
        {sortedPosts.map((post) => (
          <Link
            key={post.slug}
            to={`/blog/${post.slug}`}
            className="card card-hover p-5 block group"
          >
            <div className="flex flex-wrap items-center gap-3 mb-2 text-xs text-[var(--color-text-muted)]">
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {post.date}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {post.readTime}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-[var(--color-text)] mb-1.5 group-hover:text-[var(--color-accent)] transition-colors">
              {post.title}
            </h2>
            <p className="text-sm text-[var(--color-text-secondary)] mb-3 line-clamp-2">
              {post.summary}
            </p>
            <div className="flex flex-wrap gap-1.5">
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
          </Link>
        ))}
      </div>
    </div>
  );
}
