#!/usr/bin/env python3
"""
HTML转PPT测试脚本
使用新的html2pptx转换器进行测试
"""

import os
import time
from html2pptx import ConversionConfig, convert_html_to_ppt


def run_test(html_file, output_file, description, debug=False):
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"输入: {html_file}")
    print(f"输出: {output_file}")
    print(f"{'='*60}")

    if not os.path.exists(html_file):
        print(f"❌ 文件不存在: {html_file}")
        return False

    try:
        # 配置转换参数
        config = ConversionConfig()
        config.DEBUG_MODE = debug
        config.VERBOSE_LOGGING = debug
        config.PRESERVE_BACKGROUND = True
        config.PRESERVE_COLORS = True
        config.PRESERVE_FONTS = True
        config.PRESERVE_LAYOUT = True
        config.AUTO_FIT_TEXT = True

        start_time = time.time()
        result = convert_html_to_ppt(html_file, output_file, config)
        end_time = time.time()

        print(f"✅ 转换成功: {result}")
        print(f"⏱️  耗时: {end_time - start_time:.2f}秒")
        return True

    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("HTML转PPT终极转换器测试")
    print("版本: 2.0 - 终极版")
    print("时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    tests = [{
        "html_file": "ppt-demo.html",
        "output_file": "final-simple-output.pptx",
        "description": "简单HTML模板测试（确保文字不丢失）",
        "debug": True
    }, {
        "html_file": "ppt-demo-advanced.html",
        "output_file": "final-advanced-output.pptx",
        "description": "高级HTML模板测试（复杂元素）",
        "debug": True
    }, {
        "html_file": "complex-demo.html",
        "output_file": "final-complex-output.pptx",
        "description": "复杂HTML模板测试（完整功能验证）",
        "debug": True
    }]

    # 运行所有测试
    success_count = 0
    total_count = len(tests)

    for test in tests:
        success = run_test(test["html_file"], test["output_file"],
                           test["description"], test["debug"])
        if success:
            success_count += 1

    # 输出测试结果
    print(f"\n{'='*60}")
    print(f"测试完成")
    print(f"成功: {success_count}/{total_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    print(f"{'='*60}")

    # 列出生成的文件
    print("\n生成的PPT文件:")
    for test in tests:
        output_file = test["output_file"]
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024  # KB
            print(f"  📄 {output_file} ({file_size:.1f} KB)")
        else:
            print(f"  ❌ {output_file} (未生成)")

    print("\n功能验证清单:")
    print("✅ 文字完整性 - 检查是否有文字丢失")
    print("✅ 背景保持 - 检查背景色是否正确")
    print("✅ 字体样式 - 检查字体大小、颜色、粗细")
    print("✅ 布局还原 - 检查标题、列表、段落布局")
    print("✅ 列表格式 - 检查有序/无序列表")
    print("✅ 颜色一致性 - 检查文字和背景颜色")

    print("\n使用说明:")
    print("1. 打开生成的.pptx文件与HTML文件对比")
    print("2. 检查上述功能验证清单各项")
    print("3. 如发现问题，查看调试日志进行分析")


if __name__ == "__main__":
    main()
