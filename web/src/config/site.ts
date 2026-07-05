/**
 * 站点全局可配置变量
 * 修改此处即可自定义站点信息、模型列表等
 */

export const siteConfig = {
  /** 网站标题 */
  site_title: import.meta.env.VITE_SITE_TITLE || 'Mahongwei Studio',

  /** 运营组织名称 */
  organization_name: import.meta.env.VITE_ORG_NAME || 'Mahongwei Studio',

  /** ICP 备案编号 */
  icp_number: import.meta.env.VITE_ICP_NUMBER || '沪ICP备2026029396号',

  /** 联系邮箱 */
  contact_email: import.meta.env.VITE_CONTACT_EMAIL || 'mhwwangyi@163.com',

  /** 可选大模型列表（AI 前沿探索模块使用） */
  model_options: [
    { id: 'deepseek-v4-flash', name: 'DeepSeek V4 Flash', provider: '百炼' },
    { id: 'deepseek-v3', name: 'DeepSeek V3', provider: '百炼' },
    { id: 'qwen-plus', name: '通义千问 Plus', provider: '百炼' },
    { id: 'qwen-max', name: '通义千问 Max', provider: '百炼' },
  ],

  /** GitHub 仓库地址 */
  github_url: import.meta.env.VITE_GITHUB_URL || 'https://github.com/howellma35/work_studio',

  /** AI 后端 API 基础地址（Docker 环境用相对路径，本地开发可设置环境变量） */
  aiServerUrl: import.meta.env.VITE_AI_SERVER_URL || '',
};

export type SiteConfig = typeof siteConfig;
export type ModelOption = (typeof siteConfig.model_options)[number];
