import { Link } from 'react-router-dom';
import { Calendar, Clock, Tag } from 'lucide-react';
import blogs from '../../data/blogs.json';

interface BlogMeta {
  slug: string;
  title: string;
  summary: string;
  tags: string[];
  date: string;
  readTime: string;
}

export default function BlogList() {
  const posts = blogs as BlogMeta[];

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
          技术博客
        </h1>
        <p className="text-[var(--color-text-secondary)]">深度技术文章，记录学习与实践</p>
      </div>

      <div className="grid gap-6">
        {posts.map((post) => (
          <Link
            key={post.slug}
            to={`/blog/${post.slug}`}
            className="glass-card glass-card-hover p-6 block group"
          >
            <div className="flex flex-wrap items-center gap-3 mb-3 text-xs text-[var(--color-text-secondary)]">
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {post.date}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {post.readTime}
              </span>
            </div>
            <h2 className="text-xl font-bold text-[var(--color-text-primary)] mb-2 group-hover:text-[var(--color-accent-light)] transition-colors">
              {post.title}
            </h2>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4 line-clamp-2">
              {post.summary}
            </p>
            <div className="flex flex-wrap gap-2">
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
          </Link>
        ))}
      </div>
    </div>
  );
}
