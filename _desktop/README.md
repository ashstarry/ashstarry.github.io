# ashstarry · 个人作品集源码

这是 [ashstarry.github.io](https://ashstarry.github.io/) 的 React / Vite 源码。

首页先介绍创作者和三个作品，再用 Windows 95 的窗口交互承载体验：

- **Callay**：Mac 输入法，窗口里展示官网与演示。
- **Wonderline**：语音绘画，在主页内部打开真实画板。
- **Koyoi · 今宵**：互动小镇，在主页内部打开 3D 场景。

项目窗口支持放大、最小化、关闭和刷新，也保留“独立打开”作为完整浏览器体验的入口。博客目前没有文章，`/blog/` 只保留占位。

## 修改内容

- `src/personalProjects.js`：项目名称、用途、示例和网址。
- `src/components/PortfolioFolder.jsx`：个人主页内容。
- `src/css/PortfolioFolder.css`：个人主页排版与样式。
- `src/components/PersonalBrowser.jsx`：项目内嵌窗口。
- `src/icon.json`：桌面图标与工具。

## 本地开发

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run dev
```

在仓库根目录运行 `node tools/build-desktop.mjs`，可以构建并同步发布文件，保留博客占位和不发布的旧模板归档。

更详细的适配记录见 [ONBOARDING.md](ONBOARDING.md)。

## 开源致谢

桌面交互基础来自 [Yuteoctober/wins95Portfolio](https://github.com/Yuteoctober/wins95Portfolio)，按 MIT 许可证使用和改写。原始版权与许可保留在 [LICENSE](LICENSE)，上游说明保留在 [UPSTREAM-README.md](UPSTREAM-README.md)。
