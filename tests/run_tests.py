#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金爬虫测试运行器
执行所有测试并生成报告
"""

import sys
import os
import time
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_system_health():
    """系统健康检查"""
    print("🔍 执行系统健康检查...")
    
    health_results = {
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "timestamp": datetime.now().isoformat()
    }
    
    # 检查Python版本
    if sys.version_info >= (3, 7):
        print("✅ Python版本检查通过")
        health_results["python_check"] = "PASS"
    else:
        print("❌ Python版本过低")
        health_results["python_check"] = "FAIL"
    
    # 检查必要目录
    required_dirs = ["src", "config"]
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ 目录 {dir_name} 存在")
            health_results[f"{dir_name}_check"] = "PASS"
        else:
            print(f"⚠️ 目录 {dir_name} 不存在")
            health_results[f"{dir_name}_check"] = "WARN"
    
    return health_results

def test_module_imports():
    """测试模块导入"""
    print("\n📦 测试模块导入...")
    
    import_results = {}
    
    # 测试核心模块导入
    modules_to_test = [
        "gold_scraper",
        "gold_scraper.config_manager",
        "gold_scraper.fallback_manager", 
        "gold_scraper.data_validator",
        "gold_scraper.error_handler",
        "gold_scraper.performance_monitor"
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name} 导入成功")
            import_results[module_name] = "SUCCESS"
        except ImportError as e:
            print(f"❌ {module_name} 导入失败: {e}")
            import_results[module_name] = f"FAILED: {e}"
        except Exception as e:
            print(f"⚠️ {module_name} 导入异常: {e}")
            import_results[module_name] = f"ERROR: {e}"
    
    return import_results

def test_basic_functionality():
    """测试基础功能"""
    print("\n⚙️ 测试基础功能...")
    
    functionality_results = {}
    
    try:
        # 测试系统初始化
        from gold_scraper import initialize_gold_scraper, get_system_status
        
        print("🔧 测试系统初始化...")
        init_result = initialize_gold_scraper()
        functionality_results["initialization"] = "SUCCESS" if init_result else "FAILED"
        
        print("📊 测试系统状态...")
        status = get_system_status()
        functionality_results["status_check"] = "SUCCESS" if isinstance(status, dict) else "FAILED"
        
        # 测试降级管理器
        from gold_scraper import get_fallback_manager
        print("🔄 测试降级管理器...")
        manager = get_fallback_manager()
        preferred = manager.get_preferred_source()
        functionality_results["fallback_manager"] = "SUCCESS" if preferred else "FAILED"
        
        # 测试数据验证器
        from gold_scraper import get_data_validator
        print("✅ 测试数据验证器...")
        validator = get_data_validator()
        test_data = {"status": "success", "items": []}
        result = validator.validate_gold_data(test_data)
        functionality_results["data_validator"] = "SUCCESS" if result else "FAILED"
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        functionality_results["error"] = str(e)
    
    return functionality_results

def run_unit_tests():
    """运行单元测试"""
    print("\n🧪 运行单元测试...")
    
    try:
        from test_gold_scraper_mvp import run_mvp_tests
        result = run_mvp_tests()
        
        return {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success_rate": (result.testsRun - len(result.failures) - len(result.errors)) / max(result.testsRun, 1) * 100
        }
    except Exception as e:
        print(f"❌ 单元测试运行失败: {e}")
        return {"error": str(e)}

def generate_test_report(health_results, import_results, functionality_results, unit_test_results):
    """生成测试报告"""
    print("\n📋 生成测试报告...")
    
    report = {
        "test_timestamp": datetime.now().isoformat(),
        "system_health": health_results,
        "module_imports": import_results,
        "basic_functionality": functionality_results,
        "unit_tests": unit_test_results
    }
    
    # 计算总体评分
    total_score = 0
    max_score = 0
    
    # 导入测试评分
    import_success = sum(1 for result in import_results.values() if result == "SUCCESS")
    import_total = len(import_results)
    if import_total > 0:
        total_score += (import_success / import_total) * 30
    max_score += 30
    
    # 功能测试评分
    func_success = sum(1 for result in functionality_results.values() if result == "SUCCESS")
    func_total = len([k for k in functionality_results.keys() if k != "error"])
    if func_total > 0:
        total_score += (func_success / func_total) * 40
    max_score += 40
    
    # 单元测试评分
    if "success_rate" in unit_test_results:
        total_score += (unit_test_results["success_rate"] / 100) * 30
    max_score += 30
    
    overall_score = (total_score / max_score) * 100 if max_score > 0 else 0
    report["overall_score"] = overall_score
    
    # 输出报告摘要
    print(f"\n📊 测试报告摘要:")
    print(f"总体评分: {overall_score:.1f}/100")
    print(f"模块导入: {import_success}/{import_total} 成功")
    print(f"基础功能: {func_success}/{func_total} 成功")
    
    if "success_rate" in unit_test_results:
        print(f"单元测试: {unit_test_results['success_rate']:.1f}% 成功率")
    
    return report

def main():
    """主函数"""
    print("🚀 开始黄金爬虫系统测试...")
    start_time = time.time()
    
    # 执行各项测试
    health_results = test_system_health()
    import_results = test_module_imports()
    functionality_results = test_basic_functionality()
    unit_test_results = run_unit_tests()
    
    # 生成报告
    report = generate_test_report(health_results, import_results, functionality_results, unit_test_results)
    
    # 计算总耗时
    total_time = time.time() - start_time
    print(f"\n⏱️ 测试总耗时: {total_time:.2f} 秒")
    
    # 输出最终结果
    if report["overall_score"] >= 80:
        print("🎉 测试通过！系统可以部署")
        return 0
    elif report["overall_score"] >= 60:
        print("⚠️ 测试基本通过，但需要改进")
        return 1
    else:
        print("❌ 测试失败，需要修复问题")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)