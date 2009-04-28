/*Instance 1 of interruption isr1*/

#include "embUnit.h"
#include "tpl_os.h"

/*test case:test the reaction of the system called with 
 an activation of a isr*/
static void test_isr1_instance1(void)
{
	StatusType result_inst_1;
	
	SCHEDULING_CHECK_INIT(6);
	result_inst_1 = GetActiveApplicationMode();
	SCHEDULING_CHECK_AND_EQUAL_INT(6,E_OK , result_inst_1);
	
}

/*create the test suite with all the test cases*/
TestRef HookTest_seq4_isr1_instance1(void)
{
	EMB_UNIT_TESTFIXTURES(fixtures) {
		new_TestFixture("test_isr1_instance1",test_isr1_instance1)
	};
	EMB_UNIT_TESTCALLER(HookTest,"HookTest_sequence4",NULL,NULL,fixtures);
	
	return (TestRef)&HookTest;
}