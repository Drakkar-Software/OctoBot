import React, {type ReactNode} from 'react';
import BlogPostItem from '@theme-original/BlogPostItem';
import type BlogPostItemType from '@theme/BlogPostItem';
import type {WrapperProps} from '@docusaurus/types';
import {useBlogPost} from '@docusaurus/plugin-content-blog/client';
import Link from '@docusaurus/Link';

type Props = WrapperProps<typeof BlogPostItemType>;

function CoverImage(): ReactNode {
  const {metadata, frontMatter, isBlogPostPage} = useBlogPost();

  // Only show in list view, not on the full post page
  if (isBlogPostPage) return null;

  const image = frontMatter.image as string | undefined;
  if (!image) return null;

  return (
    <Link to={metadata.permalink} className="blog-post-cover-link">
      <img
        src={image}
        alt={metadata.title}
        className="blog-post-cover-image"
        loading="lazy"
      />
    </Link>
  );
}

export default function BlogPostItemWrapper(props: Props): ReactNode {
  return (
    <div className="blog-post-card">
      <CoverImage />
      <BlogPostItem {...props} />
    </div>
  );
}
